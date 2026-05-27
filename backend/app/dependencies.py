from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthScheme, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CashRegisterClosedException, ForbiddenException, NotFoundException, UnauthorizedException
from app.core.security import decode_access_token
from app.database import get_db

security_scheme = HTTPBearer(auto_error=False)


async def get_current_token_payload(
    request: Request,
    authorization: str | None = Header(None),
) -> dict:
    if not authorization:
        raise UnauthorizedException("Token requerido")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedException("Formato de token inválido")

    payload = decode_access_token(token)
    if not payload:
        raise UnauthorizedException("Token inválido o expirado")

    request.state.token_payload = payload
    request.state.user_id = UUID(payload["sub"])
    request.state.tenant_id = UUID(payload["tenant_id"])
    request.state.role = payload["role"]
    request.state.permissions = payload.get("permissions", [])
    raw_session_id = payload.get("session_id")
    if not raw_session_id:
        raise UnauthorizedException("Token inválido: sin session_id")
    request.state.session_id = UUID(raw_session_id)

    return payload


async def get_current_user_id(request: Request) -> UUID:
    return request.state.user_id


async def get_current_tenant_id(request: Request) -> UUID:
    return request.state.tenant_id


async def validate_cash_register_open(
    cash_register_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant_id),
):
    result = await db.execute(
        text("""
            SELECT status FROM cash_registers
            WHERE id = :id AND tenant_id = :tenant_id
        """),
        {"id": cash_register_id, "tenant_id": tenant_id},
    )
    row = result.fetchone()
    if not row:
        raise NotFoundException("Caja no encontrada")
    if row.status != "open":
        raise CashRegisterClosedException()
    return cash_register_id
