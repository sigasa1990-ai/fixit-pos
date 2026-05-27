from uuid import UUID

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantMixin, TimestampMixin


class Warehouse(BaseModel, TenantMixin, TimestampMixin):
    __tablename__ = "warehouses"

    branch_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str | None] = mapped_column(String(50), default="warehouse")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Location(BaseModel, TenantMixin, TimestampMixin):
    __tablename__ = "locations"

    warehouse_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
