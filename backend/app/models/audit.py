from uuid import UUID

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TenantMixin


class AuditLog(BaseModel, TenantMixin):
    __tablename__ = "audit_logs"

    user_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[UUID | None] = mapped_column(UUIDType(as_uuid=True))
    description: Mapped[str | None] = mapped_column(Text)
    old_values: Mapped[dict | None] = mapped_column(JSONB)
    new_values: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
