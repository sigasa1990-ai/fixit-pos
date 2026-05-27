from uuid import UUID

from sqlalchemy import DECIMAL, String, Text
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantMixin, TimestampMixin


class Inventory(BaseModel, TenantMixin, TimestampMixin):
    __tablename__ = "inventory"

    product_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    location_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    quantity: Mapped[float] = mapped_column(DECIMAL(12, 4), nullable=False, default=0)
    min_stock: Mapped[float] = mapped_column(DECIMAL(12, 4), default=0)
    max_stock: Mapped[float | None] = mapped_column(DECIMAL(12, 4))


class InventoryMovement(BaseModel, TenantMixin):
    __tablename__ = "inventory_movements"

    product_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    location_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50))
    reference_id: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    quantity_before: Mapped[float] = mapped_column(DECIMAL(12, 4), nullable=False)
    quantity_change: Mapped[float] = mapped_column(DECIMAL(12, 4), nullable=False)
    quantity_after: Mapped[float] = mapped_column(DECIMAL(12, 4), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
