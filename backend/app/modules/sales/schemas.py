from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentInput(BaseModel):
    payment_method: str = Field(..., pattern="^(cash|card|transfer|usd)$")
    currency: str = Field(default="MXN", pattern="^(MXN|USD)$")
    amount: float = Field(..., gt=0)
    exchange_rate: float = Field(default=1.0000, gt=0)
    reference: str | None = None
    bank: str | None = None
    authorization_code: str | None = None
    last_four_digits: str | None = Field(None, pattern="^\\d{4}$")
    card_type: str | None = None


class SaleItemInput(BaseModel):
    product_id: UUID
    location_id: UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    discount: float = Field(default=0, ge=0)
    tax_rate: float = Field(default=0.00, ge=0)


class CreateSaleRequest(BaseModel):
    branch_id: UUID
    cash_register_id: UUID
    customer_id: UUID | None = None
    items: list[SaleItemInput] = Field(..., min_length=1)
    payments: list[PaymentInput] = Field(..., min_length=1)
    notes: str | None = None


class CancelSaleRequest(BaseModel):
    reason: str = Field(..., min_length=1)
    admin_pin: str | None = None


class SaleResponse(BaseModel):
    id: UUID
    folio: str
    status: str
    subtotal: float
    tax_total: float
    discount_total: float
    total: float
    payment_status: str
    items_count: int
    user_id: UUID
    customer_id: UUID | None
    branch_id: UUID
    cash_register_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
