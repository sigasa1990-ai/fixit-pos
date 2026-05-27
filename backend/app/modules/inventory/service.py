from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import InsufficientStockException, NotFoundException


async def get_inventory_by_location(
    db: AsyncSession,
    tenant_id: UUID,
    location_id: UUID | None = None,
    product_id: UUID | None = None,
    branch_id: UUID | None = None,
) -> list[dict]:
    conditions = ["i.tenant_id = :tenant_id"]
    params = {"tenant_id": tenant_id}

    if location_id:
        conditions.append("i.location_id = :location_id")
        params["location_id"] = location_id
    if product_id:
        conditions.append("i.product_id = :product_id")
        params["product_id"] = product_id
    if branch_id:
        conditions.append("i.branch_id = :branch_id")
        params["branch_id"] = branch_id

    where = " AND ".join(conditions)
    result = await db.execute(
        text(f"""
            SELECT i.*, p.name as product_name, p.product_code,
                   l.name as location_name, w.name as warehouse_name
            FROM inventory i
            JOIN products p ON p.id = i.product_id
            JOIN locations l ON l.id = i.location_id
            JOIN warehouses w ON w.id = i.warehouse_id
            WHERE {where}
            ORDER BY p.name
        """),
        params,
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def validate_stock(
    db: AsyncSession,
    tenant_id: UUID,
    items: list[dict],
) -> list[dict]:
    results = []
    for item in items:
        product_id = item["product_id"]
        location_id = item["location_id"]
        quantity = item["quantity"]

        result = await db.execute(
            text("""
                SELECT i.quantity, p.name as product_name
                FROM inventory i
                JOIN products p ON p.id = i.product_id
                WHERE i.tenant_id = :tenant_id
                  AND i.product_id = :product_id
                  AND i.location_id = :location_id
                FOR UPDATE
            """),
            {
                "tenant_id": tenant_id,
                "product_id": product_id,
                "location_id": location_id,
            },
        )
        row = result.fetchone()

        current_stock = row.quantity if row else 0
        product_name = row.product_name if row else "Desconocido"

        available = current_stock >= quantity
        if not available:
            raise InsufficientStockException(product_name)

        results.append({
            "available": True,
            "product_id": product_id,
            "product_name": product_name,
            "current_stock": float(current_stock),
            "requested": quantity,
        })

    return results


async def deduct_stock(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    location_id: UUID,
    quantity: float,
    reference_type: str,
    reference_id: UUID,
):
    result = await db.execute(
        text("""
            UPDATE inventory
            SET quantity = quantity - :quantity,
                updated_at = NOW()
            WHERE tenant_id = :tenant_id
              AND product_id = :product_id
              AND location_id = :location_id
              AND quantity >= :quantity
            RETURNING quantity, (quantity + :quantity) as old_qty
        """),
        {
            "tenant_id": tenant_id,
            "product_id": product_id,
            "location_id": location_id,
            "quantity": quantity,
        },
    )
    row = result.fetchone()
    if not row:
        product = await db.execute(
            text("SELECT name FROM products WHERE id = :id"),
            {"id": product_id},
        )
        pname = product.scalar() or "Producto"
        raise InsufficientStockException(pname)

    await db.execute(
        text("""
            INSERT INTO inventory_movements (
                tenant_id, product_id, warehouse_id, location_id, branch_id,
                user_id, movement_type, reference_type, reference_id,
                quantity_before, quantity_change, quantity_after
            )
            SELECT :tenant_id, :product_id, i.warehouse_id, i.location_id, i.branch_id,
                   :user_id, 'sale', :ref_type, :ref_id,
                   :old_qty, -:quantity, i.quantity
            FROM inventory i
            WHERE i.tenant_id = :tenant_id
              AND i.product_id = :product_id
              AND i.location_id = :location_id
        """),
        {
            "tenant_id": tenant_id,
            "product_id": product_id,
            "location_id": location_id,
            "user_id": user_id,
            "quantity": quantity,
            "old_qty": float(row.old_qty),
            "ref_type": reference_type,
            "ref_id": reference_id,
        },
    )


async def transfer_stock(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    from_location_id: UUID,
    to_location_id: UUID,
    quantity: float,
    notes: str | None = None,
):
    await deduct_stock(
        db, tenant_id, user_id, product_id, from_location_id,
        quantity, "transfer", from_location_id,
    )

    result = await db.execute(
        text("""
            UPDATE inventory
            SET quantity = quantity + :quantity, updated_at = NOW()
            WHERE tenant_id = :tenant_id
              AND product_id = :product_id
              AND location_id = :location_id
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "product_id": product_id,
            "location_id": to_location_id,
            "quantity": quantity,
        },
    )
    row = result.fetchone()
    if not row:
        raise NotFoundException("Ubicación destino no tiene registro de inventario")


async def adjust_stock(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    location_id: UUID,
    new_quantity: float,
    reason: str,
    ip_address: str | None = None,
):
    result = await db.execute(
        text("""
            UPDATE inventory
            SET quantity = :new_qty, updated_at = NOW()
            WHERE tenant_id = :tenant_id
              AND product_id = :product_id
              AND location_id = :location_id
            RETURNING quantity, (SELECT quantity FROM inventory
                WHERE tenant_id = :tenant_id2
                  AND product_id = :product_id2
                  AND location_id = :location_id2) as old_qty
        """),
        {
            "tenant_id": tenant_id,
            "product_id": product_id,
            "location_id": location_id,
            "new_qty": new_quantity,
            "tenant_id2": tenant_id,
            "product_id2": product_id,
            "location_id2": location_id,
        },
    )
    row = result.fetchone()
    if not row:
        raise NotFoundException("Registro de inventario no encontrado")

    await log_audit(
        db=db, tenant_id=tenant_id, user_id=user_id,
        action="inventory.adjust", entity_type="inventory",
        description=f"Ajuste de inventario: {reason}",
        old_values={"quantity": float(row.old_qty)},
        new_values={"quantity": new_quantity},
        ip_address=ip_address,
    )
