from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException


async def generate_folio(
    db: AsyncSession,
    tenant_id: UUID,
    branch_id: UUID,
    cash_register_id: UUID,
    document_type: str,
) -> str:
    result = await db.execute(
        text("""
            UPDATE folio_controls
            SET current_number = next_number,
                next_number = next_number + 1,
                updated_at = NOW()
            WHERE tenant_id = :tenant_id
              AND branch_id = :branch_id
              AND cash_register_id = :cash_register_id
              AND document_type = :document_type
            RETURNING prefix, current_number
        """),
        {
            "tenant_id": tenant_id,
            "branch_id": branch_id,
            "cash_register_id": cash_register_id,
            "document_type": document_type,
        },
    )
    row = result.fetchone()
    if not row:
        raise AppException(
            f"Control de folios no encontrado para tenant={tenant_id}, "
            f"branch={branch_id}, register={cash_register_id}, type={document_type}"
        )
    prefix, number = row.prefix, row.current_number
    return f"{prefix}{number:06d}"


async def ensure_folio_control_exists(
    db: AsyncSession,
    tenant_id: UUID,
    branch_id: UUID,
    cash_register_id: UUID,
    document_type: str,
    prefix: str,
):
    result = await db.execute(
        text("""
            INSERT INTO folio_controls (tenant_id, branch_id, cash_register_id, document_type, prefix)
            VALUES (:tenant_id, :branch_id, :cash_register_id, :document_type, :prefix)
            ON CONFLICT (tenant_id, branch_id, cash_register_id, document_type)
            DO NOTHING
        """),
        {
            "tenant_id": tenant_id,
            "branch_id": branch_id,
            "cash_register_id": cash_register_id,
            "document_type": document_type,
            "prefix": prefix,
        },
    )
