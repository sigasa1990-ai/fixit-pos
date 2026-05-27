from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DECIMAL, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantMixin, TimestampMixin


class CashRegister(BaseModel, TenantMixin, TimestampMixin):
    __tablename__ = "cash_registers"

    branch_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    location_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="closed")
    current_balance: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    opening_balance: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_by: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    closed_by: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CashRegisterSession(BaseModel, TenantMixin):
    __tablename__ = "cash_register_sessions"

    cash_register_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    opened_by: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    closed_by: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    opening_balance: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    closing_balance: Mapped[float | None] = mapped_column(DECIMAL(12, 2))
    expected_balance: Mapped[float | None] = mapped_column(DECIMAL(12, 2))
    difference: Mapped[float | None] = mapped_column(DECIMAL(12, 2))
    total_cash_sales: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    total_card_sales: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    total_transfer_sales: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    total_usd_sales: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    total_cash_in: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    total_cash_out: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    total_sales_count: Mapped[int] = mapped_column(default=0)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class CashRegisterMovement(BaseModel, TenantMixin):
    __tablename__ = "cash_register_movements"

    cash_register_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    cash_register_session_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    balance_before: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    balance_after: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    reference_type: Mapped[str | None] = mapped_column(String(50))
    reference_id: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    description: Mapped[str | None] = mapped_column(Text)
