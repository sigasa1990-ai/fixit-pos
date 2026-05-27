from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import ConflictException, NotFoundException


async def generate_product_code(db: AsyncSession, tenant_id: UUID) -> str:
    result = await db.execute(
        text("""
            SELECT COALESCE(MAX(CAST(SUBSTRING(product_code FROM 5) AS INTEGER)), 0) + 1
            FROM products
            WHERE tenant_id = :tenant_id
              AND product_code ~ '^PRD-\\d{6}$'
        """),
        {"tenant_id": tenant_id},
    )
    next_num = result.scalar() or 1
    return f"PRD-{next_num:06d}"


async def create_product(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    data: dict,
    ip_address: str | None = None,
) -> dict:
    product_code = data.get("product_code") or await generate_product_code(db, tenant_id)

    if data.get("barcode"):
        existing = await db.execute(
            text("SELECT id FROM products WHERE tenant_id = :tid AND barcode = :bc"),
            {"tid": tenant_id, "bc": data["barcode"]},
        )
        if existing.fetchone():
            raise ConflictException("El código de barras ya existe")

    result = await db.execute(
        text("""
            INSERT INTO products (
                tenant_id, category_id, product_code, barcode, sku,
                name, description, price, cost, min_price,
                tax_rate, unit, warranty_days, warranty_type,
                is_service, track_inventory, notes
            ) VALUES (
                :tenant_id, :category_id, :product_code, :barcode, :sku,
                :name, :description, :price, :cost, :min_price,
                :tax_rate, :unit, :warranty_days, :warranty_type,
                :is_service, :track_inventory, :notes
            )
            RETURNING id, product_code, created_at
        """),
        {
            "tenant_id": tenant_id,
            "category_id": data.get("category_id"),
            "product_code": product_code,
            "barcode": data.get("barcode"),
            "sku": data.get("sku"),
            "name": data["name"],
            "description": data.get("description"),
            "price": data["price"],
            "cost": data["cost"],
            "min_price": data.get("min_price"),
            "tax_rate": data.get("tax_rate", 0),
            "unit": data.get("unit", "pza"),
            "warranty_days": data.get("warranty_days", 0),
            "warranty_type": data.get("warranty_type", "none"),
            "is_service": data.get("is_service", False),
            "track_inventory": data.get("track_inventory", True),
            "notes": data.get("notes"),
        },
    )
    row = result.fetchone()

    await log_audit(
        db=db, tenant_id=tenant_id, user_id=user_id,
        action="product.create", entity_type="product",
        entity_id=row.id,
        description=f"Producto creado: {data['name']} ({product_code})",
        new_values=data, ip_address=ip_address,
    )

    return {"id": row.id, "product_code": row.product_code, "created_at": row.created_at}


async def search_products(
    db: AsyncSession,
    tenant_id: UUID,
    query: str | None = None,
    category_id: UUID | None = None,
    is_active: bool = True,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    conditions = ["p.tenant_id = :tenant_id", "p.is_active = :is_active"]
    params = {"tenant_id": tenant_id, "is_active": is_active}

    if query:
        conditions.append("""
            (p.name ILIKE :query
             OR p.product_code ILIKE :q_exact
             OR p.barcode = :q_exact
             OR p.sku ILIKE :q_exact)
        """)
        params["query"] = f"%{query}%"
        params["q_exact"] = query

    if category_id:
        conditions.append("p.category_id = :category_id")
        params["category_id"] = category_id

    where_clause = " AND ".join(conditions)

    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM products p WHERE {where_clause}"),
        params,
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        text(f"""
            SELECT p.*, pc.name as category_name
            FROM products p
            LEFT JOIN product_categories pc ON pc.id = p.category_id
            WHERE {where_clause}
            ORDER BY p.name
            LIMIT :limit OFFSET :offset
        """),
        {**params, "limit": page_size, "offset": offset},
    )
    rows = result.fetchall()

    return {
        "items": [dict(row._mapping) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": -(-total // page_size) if total > 0 else 0,
    }


async def get_product(db: AsyncSession, tenant_id: UUID, product_id: UUID) -> dict | None:
    result = await db.execute(
        text("""
            SELECT p.*, pc.name as category_name
            FROM products p
            LEFT JOIN product_categories pc ON pc.id = p.category_id
            WHERE p.id = :id AND p.tenant_id = :tenant_id
        """),
        {"id": product_id, "tenant_id": tenant_id},
    )
    row = result.fetchone()
    if not row:
        raise NotFoundException("Producto no encontrado")
    return dict(row._mapping)


async def update_product(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    data: dict,
    ip_address: str | None = None,
) -> dict:
    existing = await db.execute(
        text("SELECT * FROM products WHERE id = :id AND tenant_id = :tenant_id"),
        {"id": product_id, "tenant_id": tenant_id},
    )
    row = existing.fetchone()
    if not row:
        raise NotFoundException("Producto no encontrado")

    old_values = dict(row._mapping)

    set_parts = []
    params = {"id": product_id}
    for key, value in data.items():
        if value is not None and key in (
            "category_id", "barcode", "sku", "name", "description",
            "price", "cost", "min_price", "tax_rate", "unit",
            "warranty_days", "warranty_type", "is_active", "notes",
        ):
            set_parts.append(f"{key} = :{key}")
            params[key] = value

    if not set_parts:
        return old_values

    set_parts.append("updated_at = NOW()")
    set_clause = ", ".join(set_parts)

    await db.execute(
        text(f"UPDATE products SET {set_clause} WHERE id = :id"),
        params,
    )

    await log_audit(
        db=db, tenant_id=tenant_id, user_id=user_id,
        action="product.update", entity_type="product",
        entity_id=product_id,
        description=f"Producto actualizado: {old_values.get('name')}",
        old_values=old_values, new_values=data, ip_address=ip_address,
    )

    return await get_product(db, tenant_id, product_id)
