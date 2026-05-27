from sqlalchemy import Boolean, DECIMAL, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantMixin, TimestampMixin


class Customer(BaseModel, TenantMixin, TimestampMixin):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    rfc: Mapped[str | None] = mapped_column(String(13))
    business_name: Mapped[str | None] = mapped_column(String(255))
    tax_regime: Mapped[str | None] = mapped_column(String(50))
    cfdi_usage: Mapped[str | None] = mapped_column(String(10), default="G01")
    tax_address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    credit_limit: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)
