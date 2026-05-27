from uuid import UUID

from sqlalchemy import Boolean, DECIMAL, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantMixin, TimestampMixin


class ProductCategory(BaseModel, TenantMixin, TimestampMixin):
    __tablename__ = "product_categories"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(BaseModel, TenantMixin, TimestampMixin):
    __tablename__ = "products"

    category_id: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(100))
    sku: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    cost: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    min_price: Mapped[float | None] = mapped_column(DECIMAL(12, 2))
    tax_rate: Mapped[float] = mapped_column(DECIMAL(5, 2), default=0.00)
    unit: Mapped[str] = mapped_column(String(50), default="pza")
    warranty_days: Mapped[int] = mapped_column(Integer, default=0)
    warranty_type: Mapped[str] = mapped_column(String(20), default="none")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_service: Mapped[bool] = mapped_column(Boolean, default=False)
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=True)
    image_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
