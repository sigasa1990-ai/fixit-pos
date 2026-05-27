from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.database import get_db
from app.dependencies import get_current_tenant_id, get_current_user_id
from app.modules.customers.schemas import CustomerCreate, CustomerUpdate
from app.modules.customers.service import create_customer, get_customer, search_customers, update_customer

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.post("")
async def api_create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("customer.create")),
):
    result = await create_customer(db, tenant_id, body.model_dump(exclude_none=True))
    return result


@router.get("/search")
async def api_search_customers(
    query: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("customer.read")),
):
    return await search_customers(db, tenant_id, query, page, page_size)


@router.get("/{customer_id}")
async def api_get_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("customer.read")),
):
    import uuid
    return await get_customer(db, tenant_id, uuid.UUID(customer_id))


@router.patch("/{customer_id}")
async def api_update_customer(
    customer_id: str,
    body: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("customer.update")),
):
    import uuid
    return await update_customer(
        db, tenant_id, uuid.UUID(customer_id),
        body.model_dump(exclude_none=True),
    )
