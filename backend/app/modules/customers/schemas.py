from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = None
    email: str | None = None
    rfc: str | None = Field(None, max_length=13)
    business_name: str | None = None
    tax_regime: str | None = None
    cfdi_usage: str = "G01"
    tax_address: str | None = None
    notes: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    phone: str | None = None
    email: str | None = None
    rfc: str | None = None
    business_name: str | None = None
    tax_regime: str | None = None
    cfdi_usage: str | None = None
    tax_address: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class CustomerResponse(BaseModel):
    id: UUID
    name: str
    phone: str | None
    email: str | None
    rfc: str | None
    business_name: str | None
    tax_regime: str | None
    cfdi_usage: str | None
    tax_address: str | None
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
