from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.database import get_db
from app.dependencies import get_current_tenant_id, get_current_user_id, get_current_token_payload
from app.modules.quotations.schemas import ConvertQuotationRequest, CreateQuotationRequest
from app.modules.quotations.service import convert_to_sale, create_quotation, get_quotation, search_quotations

router = APIRouter(prefix="/api/v1/quotations", tags=["quotations"])


@router.post("")
async def api_create_quotation(
    request: Request,
    body: CreateQuotationRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("quotation.create")),
):
    ip = request.client.host if request.client else None
    return await create_quotation(
        db, tenant_id, user_id, body.branch_id, body.cash_register_id,
        body.customer_id, [i.model_dump() for i in body.items],
        body.valid_until, body.notes, ip,
    )


@router.get("/search")
async def api_search_quotations(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    token_payload=Depends(get_current_token_payload),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("quotation.read")),
):
    is_admin = token_payload.get("role") == "admin"
    permissions = token_payload.get("permissions", [])
    filter_user = None if is_admin or "report.read_global" in permissions else user_id
    return await search_quotations(db, tenant_id, filter_user, status, page, page_size, is_admin)


@router.get("/{quotation_id}")
async def api_get_quotation(
    quotation_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("quotation.read")),
):
    import uuid
    return await get_quotation(db, tenant_id, uuid.UUID(quotation_id))


@router.post("/{quotation_id}/convert")
async def api_convert_quotation(
    request: Request,
    quotation_id: str,
    body: ConvertQuotationRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("quotation.convert")),
):
    ip = request.client.host if request.client else None
    import uuid
    payments = [p.model_dump() for p in body.payments] if body.payments else None
    return await convert_to_sale(
        db, tenant_id, user_id, uuid.UUID(quotation_id),
        body.cash_register_id, body.location_id, payments, ip,
    )
