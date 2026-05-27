from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException


async def create_customer(
    db: AsyncSession,
    tenant_id: UUID,
    data: dict,
) -> dict:
    result = await db.execute(
        text("""
            INSERT INTO customers (
                tenant_id, name, phone, email, rfc, business_name,
                tax_regime, cfdi_usage, tax_address, notes
            ) VALUES (
                :tenant_id, :name, :phone, :email, :rfc, :business_name,
                :tax_regime, :cfdi_usage, :tax_address, :notes
            )
            RETURNING id, created_at
        """),
        {
            "tenant_id": tenant_id,
            "name": data["name"],
            "phone": data.get("phone"),
            "email": data.get("email"),
            "rfc": data.get("rfc"),
            "business_name": data.get("business_name"),
            "tax_regime": data.get("tax_regime"),
            "cfdi_usage": data.get("cfdi_usage", "G01"),
            "tax_address": data.get("tax_address"),
            "notes": data.get("notes"),
        },
    )
    row = result.fetchone()
    return {"id": row.id, "created_at": row.created_at}


async def search_customers(
    db: AsyncSession,
    tenant_id: UUID,
    query: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    conditions = ["tenant_id = :tenant_id", "is_active = true"]
    params = {"tenant_id": tenant_id}

    if query:
        conditions.append("""
            (name ILIKE :query
             OR phone ILIKE :q_exact
             OR rfc ILIKE :q_exact
             OR email ILIKE :query)
        """)
        params["query"] = f"%{query}%"
        params["q_exact"] = query

    where = " AND ".join(conditions)

    count = await db.execute(
        text(f"SELECT COUNT(*) FROM customers WHERE {where}"), params,
    )
    total = count.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        text(f"""
            SELECT * FROM customers
            WHERE {where}
            ORDER BY name
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": page_size, "offset": offset},
    )

    return {
        "items": [dict(row._mapping) for row in result.fetchall()],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": -(-total // page_size) if total > 0 else 0,
    }


async def get_customer(db: AsyncSession, tenant_id: UUID, customer_id: UUID) -> dict:
    result = await db.execute(
        text("SELECT * FROM customers WHERE id = :id AND tenant_id = :tenant_id"),
        {"id": customer_id, "tenant_id": tenant_id},
    )
    row = result.fetchone()
    if not row:
        raise NotFoundException("Cliente no encontrado")
    return dict(row._mapping)


async def update_customer(
    db: AsyncSession,
    tenant_id: UUID,
    customer_id: UUID,
    data: dict,
) -> dict:
    existing = await db.execute(
        text("SELECT id FROM customers WHERE id = :id AND tenant_id = :tenant_id"),
        {"id": customer_id, "tenant_id": tenant_id},
    )
    if not existing.fetchone():
        raise NotFoundException("Cliente no encontrado")

    set_parts = []
    params = {"id": customer_id}
    for key in ("name", "phone", "email", "rfc", "business_name",
                 "tax_regime", "cfdi_usage", "tax_address", "is_active", "notes"):
        if key in data and data[key] is not None:
            set_parts.append(f"{key} = :{key}")
            params[key] = data[key]

    if set_parts:
        set_parts.append("updated_at = NOW()")
        await db.execute(
            text(f"UPDATE customers SET {', '.join(set_parts)} WHERE id = :id"),
            params,
        )

    return await get_customer(db, tenant_id, customer_id)
