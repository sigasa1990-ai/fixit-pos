from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TimestampMixin


class Tenant(BaseModel, TimestampMixin):
    __tablename__ = "tenants"

    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    commercial_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rfc: Mapped[str | None] = mapped_column(String(13))
    tax_regime: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(Text)
    ticket_header: Mapped[str | None] = mapped_column(Text)
    ticket_footer: Mapped[str | None] = mapped_column(Text)
    ticket_policies: Mapped[str | None] = mapped_column(Text)
    primary_color: Mapped[str | None] = mapped_column(String(7), default="#2563eb")
    secondary_color: Mapped[str | None] = mapped_column(String(7), default="#1e40af")
    pin_timeout_minutes: Mapped[int] = mapped_column(Integer, default=10)
    max_open_orders: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict | None] = mapped_column(JSONB, default=dict)
