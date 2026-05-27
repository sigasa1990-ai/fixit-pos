from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import INET, UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TenantMixin, TimestampMixin


class User(BaseModel, TenantMixin, TimestampMixin):
    __tablename__ = "users"

    role_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_pin_change: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[str | None] = mapped_column(INET)

    role = relationship("Role", foreign_keys=[role_id], lazy="joined")
