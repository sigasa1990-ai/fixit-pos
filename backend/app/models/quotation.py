from datetime import date
from uuid import UUID

from sqlalchemy import DECIMAL, Date, String, Text
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantMixin, TimestampMixin


class Quotation(BaseModel, TenantMixin, TimestampMixin):
    __tablename__ = "quotations"

    branch_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    cash_register_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    folio: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    subtotal: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    tax_total: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    discount_total: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    total: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    converted_to_sale_id: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))


class QuotationItem(BaseModel, TenantMixin):
    __tablename__ = "quotation_items"

    quotation_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    product_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    quantity: Mapped[float] = mapped_column(DECIMAL(12, 4), nullable=False)
    unit_price: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    discount: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    tax_rate: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00)
    tax_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    subtotal: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    total: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
