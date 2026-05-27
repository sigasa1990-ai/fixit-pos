from uuid import UUID

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantMixin, TimestampMixin


class FolioControl(BaseModel, TenantMixin, TimestampMixin):
    __tablename__ = "folio_controls"

    branch_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    cash_register_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    document_type: Mapped[str] = mapped_column(String(10), nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    current_number: Mapped[int] = mapped_column(Integer, default=0)
    next_number: Mapped[int] = mapped_column(Integer, default=1)
