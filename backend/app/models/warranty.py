from datetime import date
from uuid import UUID

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantMixin, TimestampMixin


class Warranty(BaseModel, TenantMixin, TimestampMixin):
    __tablename__ = "warranties"

    sale_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    sale_item_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    product_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    warranty_type: Mapped[str] = mapped_column(String(20), default="standard")
    warranty_days: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
