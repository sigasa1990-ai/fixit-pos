from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StockCheckItem(BaseModel):
    product_id: UUID
    location_id: UUID
    quantity: float = Field(..., gt=0)


class StockCheckResponse(BaseModel):
    available: bool
    product_id: UUID
    product_name: str | None = None
    current_stock: float
    requested: float


class InventoryResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str | None = None
    product_code: str | None = None
    warehouse_id: UUID
    warehouse_name: str | None = None
    location_id: UUID
    location_name: str | None = None
    branch_id: UUID
    quantity: float
    min_stock: float
    max_stock: float | None
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryTransferRequest(BaseModel):
    product_id: UUID
    from_location_id: UUID
    to_location_id: UUID
    quantity: float = Field(..., gt=0)
    notes: str | None = None


class InventoryAdjustmentRequest(BaseModel):
    product_id: UUID
    location_id: UUID
    new_quantity: float = Field(..., ge=0)
    reason: str = Field(..., min_length=1)
