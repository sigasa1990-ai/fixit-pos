from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.database import get_db
from app.dependencies import get_current_tenant_id, get_current_user_id
from app.modules.products.schemas import ProductCreate, ProductResponse, ProductUpdate
from app.modules.products.service import create_product, get_product, search_products, update_product

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.post("")
async def api_create_product(
    request: Request,
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("product.create")),
):
    ip = request.client.host if request.client else None
    result = await create_product(db, tenant_id, user_id, body.model_dump(exclude_none=True), ip)
    return result


@router.get("/search")
async def api_search_products(
    request: Request,
    query: str | None = Query(None),
    category_id: str | None = Query(None),
    is_active: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("product.read")),
):
    import uuid
    cat_id = uuid.UUID(category_id) if category_id else None
    return await search_products(db, tenant_id, query, cat_id, is_active, page, page_size)


@router.get("/{product_id}")
async def api_get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("product.read")),
):
    import uuid
    return await get_product(db, tenant_id, uuid.UUID(product_id))


@router.patch("/{product_id}")
async def api_update_product(
    request: Request,
    product_id: str,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("product.update")),
):
    ip = request.client.host if request.client else None
    import uuid
    return await update_product(
        db, tenant_id, user_id, uuid.UUID(product_id),
        body.model_dump(exclude_none=True), ip,
    )
