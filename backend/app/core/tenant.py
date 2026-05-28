from uuid import UUID

from fastapi import Header, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_tenant_id_from_request(
    request: Request,
    x_tenant_id: str | None = Header(None),
) -> UUID | None:
    token_payload = getattr(request.state, "token_payload", None)
    if token_payload and "tenant_id" in token_payload:
        return UUID(token_payload["tenant_id"])
    if x_tenant_id:
        try:
            return UUID(x_tenant_id)
        except (ValueError, AttributeError):
            pass
    return None


async def set_tenant_context(session: AsyncSession, tenant_id: UUID):
    await session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))


async def set_user_context(session: AsyncSession, user_id: UUID):
    await session.execute(text(f"SET LOCAL app.user_id = '{user_id}'"))


async def set_role_context(session: AsyncSession, role: str):
    await session.execute(text(f"SET LOCAL app.role = '{role}'"))


async def set_session_context(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    role: str,
):
    await session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))
    await session.execute(text(f"SET LOCAL app.user_id = '{user_id}'"))
    await session.execute(text(f"SET LOCAL app.role = '{role}'"))
