from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.database import get_db
from app.dependencies import (
    get_current_tenant_id,
    get_current_user_id,
    get_current_token_payload,
)
from app.modules.sales.schemas import CancelSaleRequest, CreateSaleRequest
from app.modules.sales.service import cancel_sale, create_sale, get_sale, search_sales

router = APIRouter(prefix="/api/v1/sales", tags=["sales"])


@router.post("")
async def api_create_sale(
    request: Request,
    body: CreateSaleRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("sale.create")),
):
    ip = request.client.host if request.client else None

    # Obtener session activa de caja
    session_result = await db.execute(
        text("""
            SELECT id FROM cash_register_sessions
            WHERE cash_register_id = :cr_id
              AND tenant_id = :tenant_id
              AND closed_at IS NULL
            ORDER BY opened_at DESC
            LIMIT 1
        """),
        {"cr_id": body.cash_register_id, "tenant_id": tenant_id},
    )
    session = session_result.fetchone()
    if not session:
        from app.core.exceptions import AppException
        raise AppException("No hay sesión activa de caja. Abra la caja primero.")

    return await create_sale(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        branch_id=body.branch_id,
        cash_register_id=body.cash_register_id,
        cash_register_session_id=session.id,
        customer_id=body.customer_id,
        items=[i.model_dump() for i in body.items],
        payments=[p.model_dump() for p in body.payments],
        notes=body.notes,
        ip_address=ip,
    )


@router.get("/search")
async def api_search_sales(
    request: Request,
    user_id: str | None = Query(None),
    branch_id: str | None = Query(None),
    cash_register_id: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    folio: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    token_payload=Depends(get_current_token_payload),
    user_id_param=Depends(get_current_user_id),
    _=Depends(require_permission("sale.read")),
):
    is_admin = token_payload.get("role") == "admin"
    permissions = token_payload.get("permissions", [])

    # Si no es admin y no tiene permiso global, solo ve sus propias ventas
    filter_user_id = None if (is_admin or "sale.read_global" in permissions) else user_id_param

    parse_date = lambda s: datetime.fromisoformat(s) if s else None

    return await search_sales(
        db, tenant_id,
        user_id=UUID(filter_user_id) if filter_user_id else None,
        branch_id=UUID(branch_id) if branch_id else None,
        cash_register_id=UUID(cash_register_id) if cash_register_id else None,
        date_from=parse_date(date_from),
        date_to=parse_date(date_to),
        folio=folio,
        page=page,
        page_size=page_size,
        is_admin=is_admin or "sale.read_global" in permissions,
    )


@router.get("/{sale_id}")
async def api_get_sale(
    sale_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("sale.read")),
):
    return await get_sale(db, tenant_id, UUID(sale_id))


@router.post("/{sale_id}/cancel")
async def api_cancel_sale(
    request: Request,
    sale_id: str,
    body: CancelSaleRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("sale.cancel")),
):
    ip = request.client.host if request.client else None
    return await cancel_sale(db, tenant_id, user_id, UUID(sale_id), body.reason, ip)
