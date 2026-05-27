from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.database import get_db
from app.dependencies import get_current_tenant_id, get_current_user_id
from app.modules.inventory.schemas import (
    InventoryAdjustmentRequest,
    InventoryTransferRequest,
    StockCheckItem,
)
from app.modules.inventory.service import (
    adjust_stock,
    get_inventory_by_location,
    transfer_stock,
    validate_stock,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("")
async def api_get_inventory(
    location_id: str | None = Query(None),
    product_id: str | None = Query(None),
    branch_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("inventory.read")),
):
    import uuid
    return await get_inventory_by_location(
        db, tenant_id,
        location_id=uuid.UUID(location_id) if location_id else None,
        product_id=uuid.UUID(product_id) if product_id else None,
        branch_id=uuid.UUID(branch_id) if branch_id else None,
    )


@router.post("/validate-stock")
async def api_validate_stock(
    items: list[StockCheckItem],
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("sale.create")),
):
    return await validate_stock(
        db, tenant_id,
        [i.model_dump() for i in items],
    )


@router.post("/transfer")
async def api_transfer_stock(
    request: Request,
    body: InventoryTransferRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("inventory.transfer")),
):
    await transfer_stock(
        db, tenant_id, user_id,
        body.product_id, body.from_location_id, body.to_location_id,
        body.quantity, body.notes,
    )
    return {"message": "Transferencia exitosa"}


@router.post("/adjust")
async def api_adjust_stock(
    request: Request,
    body: InventoryAdjustmentRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("inventory.adjust")),
):
    ip = request.client.host if request.client else None
    await adjust_stock(
        db, tenant_id, user_id,
        body.product_id, body.location_id,
        body.new_quantity, body.reason, ip,
    )
    return {"message": "Ajuste aplicado"}
