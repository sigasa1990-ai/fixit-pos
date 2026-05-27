from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def log_audit(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    action: str,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    description: str | None = None,
    old_values: dict | None = None,
    new_values: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    query = text("""
        INSERT INTO audit_logs (
            tenant_id, user_id, action, entity_type, entity_id,
            description, old_values, new_values, ip_address, user_agent
        ) VALUES (
            :tenant_id, :user_id, :action, :entity_type, :entity_id,
            :description, :old_values::jsonb, :new_values::jsonb,
            :ip_address::inet, :user_agent
        )
    """)
    await db.execute(query, {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "description": description,
        "old_values": _to_json(old_values),
        "new_values": _to_json(new_values),
        "ip_address": ip_address,
        "user_agent": user_agent,
    })


def _to_json(data: dict | None) -> str | None:
    if data is None:
        return None
    import json
    return json.dumps(data, default=str)
