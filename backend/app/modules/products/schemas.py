from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    category_id: UUID | None = None
    product_code: str | None = None
    barcode: str | None = None
    sku: str | None = None
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    price: float = Field(..., gt=0)
    cost: float = Field(..., ge=0)
    min_price: float | None = None
    tax_rate: float = 0.00
    unit: str = "pza"
    warranty_days: int = 0
    warranty_type: str = "none"
    is_service: bool = False
    track_inventory: bool = True
    notes: str | None = None


class ProductUpdate(BaseModel):
    category_id: UUID | None = None
    barcode: str | None = None
    sku: str | None = None
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    price: float | None = Field(None, gt=0)
    cost: float | None = Field(None, ge=0)
    min_price: float | None = None
    tax_rate: float | None = None
    unit: str | None = None
    warranty_days: int | None = None
    warranty_type: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class ProductResponse(BaseModel):
    id: UUID
    category_id: UUID | None
    product_code: str
    barcode: str | None
    sku: str | None
    name: str
    description: str | None
    price: float
    cost: float
    min_price: float | None
    tax_rate: float
    unit: str
    warranty_days: int
    warranty_type: str
    is_active: bool
    is_service: bool
    track_inventory: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductSearchParams(BaseModel):
    query: str | None = None
    category_id: UUID | None = None
    is_active: bool | None = True
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
