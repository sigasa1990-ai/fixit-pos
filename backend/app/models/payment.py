from uuid import UUID

from sqlalchemy import DECIMAL, String, Text
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantMixin


class Payment(BaseModel, TenantMixin):
    __tablename__ = "payments"

    sale_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="MXN")
    amount: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    amount_mxn: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    exchange_rate: Mapped[float] = mapped_column(DECIMAL(10, 4), default=1.0000)
    reference: Mapped[str | None] = mapped_column(String(255))
    bank: Mapped[str | None] = mapped_column(String(100))
    authorization_code: Mapped[str | None] = mapped_column(String(50))
    last_four_digits: Mapped[str | None] = mapped_column(String(4))
    card_type: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
