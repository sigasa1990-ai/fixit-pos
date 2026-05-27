from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QuotationItemInput(BaseModel):
    product_id: UUID
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    discount: float = Field(default=0, ge=0)
    tax_rate: float = Field(default=0.00, ge=0)


class CreateQuotationRequest(BaseModel):
    branch_id: UUID
    cash_register_id: UUID
    customer_id: UUID | None = None
    items: list[QuotationItemInput] = Field(..., min_length=1)
    valid_until: date | None = None
    notes: str | None = None


class ConvertQuotationRequest(BaseModel):
    cash_register_id: UUID
    location_id: UUID
    payments: list | None = None
