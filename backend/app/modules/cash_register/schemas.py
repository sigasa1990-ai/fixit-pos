from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OpenCashRegisterRequest(BaseModel):
    cash_register_id: UUID
    opening_balance: float = Field(..., ge=0)


class CloseCashRegisterRequest(BaseModel):
    cash_register_id: UUID
    notes: str | None = None


class CashMovementRequest(BaseModel):
    cash_register_id: UUID
    amount: float = Field(..., gt=0)
    movement_type: str = Field(..., pattern="^(in|out)$")
    description: str = Field(..., min_length=1)
    reference_type: str | None = None
    reference_id: UUID | None = None


class CashRegisterResponse(BaseModel):
    id: UUID
    code: str
    name: str
    branch_id: UUID
    location_id: UUID
    status: str
    current_balance: float
    opening_balance: float
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CashRegisterSessionResponse(BaseModel):
    id: UUID
    cash_register_id: UUID
    opened_by: UUID
    opening_balance: float
    closing_balance: float | None
    expected_balance: float | None
    difference: float | None
    total_cash_sales: float
    total_card_sales: float
    total_sales_count: int
    opened_at: datetime
    closed_at: datetime | None

    class Config:
        from_attributes = True
