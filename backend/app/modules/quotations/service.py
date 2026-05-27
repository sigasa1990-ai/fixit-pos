from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import AppException, NotFoundException
from app.core.folios import generate_folio
from app.modules.sales.service import create_sale


async def create_quotation(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    branch_id: UUID,
    cash_register_id: UUID,
    customer_id: UUID | None,
    items: list[dict],
    valid_until: date | None = None,
    notes: str | None = None,
    ip_address: str | None = None,
) -> dict:
    folio = await generate_folio(db, tenant_id, branch_id, cash_register_id, "COT")

    subtotal = 0.0
    tax_total = 0.0
    discount_total = 0.0

    for item in items:
        line_subtotal = item["unit_price"] * item["quantity"]
        line_discount = item.get("discount", 0)
        line_after = line_subtotal - line_discount
        line_tax = line_after * (item.get("tax_rate", 0) / 100)
        line_total = line_after + line_tax

        item["_subtotal"] = round(line_subtotal, 2)
        item["_discount"] = round(line_discount, 2)
        item["_tax"] = round(line_tax, 2)
        item["_total"] = round(line_total, 2)

        subtotal += line_subtotal
        discount_total += line_discount
        tax_total += line_tax

    total = round(subtotal - discount_total + tax_total, 2)

    result = await db.execute(
        text("""
            INSERT INTO quotations (
                tenant_id, branch_id, cash_register_id, user_id, customer_id,
                folio, status, subtotal, tax_total, discount_total, total,
                valid_until, notes
            ) VALUES (
                :tenant_id, :branch_id, :cr_id, :user_id, :customer_id,
                :folio, 'active', :subtotal, :tax_total, :discount_total,
                :total, :valid_until, :notes
            )
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "branch_id": branch_id,
            "cr_id": cash_register_id,
            "user_id": user_id,
            "customer_id": customer_id,
            "folio": folio,
            "subtotal": round(subtotal, 2),
            "tax_total": round(tax_total, 2),
            "discount_total": round(discount_total, 2),
            "total": total,
            "valid_until": valid_until,
            "notes": notes,
        },
    )
    quotation_id = result.scalar()

    for item in items:
        await db.execute(
            text("""
                INSERT INTO quotation_items (
                    tenant_id, quotation_id, product_id,
                    quantity, unit_price, discount,
                    tax_rate, tax_amount, subtotal, total
                ) VALUES (
                    :tenant_id, :quotation_id, :product_id,
                    :quantity, :unit_price, :discount,
                    :tax_rate, :tax_amount, :subtotal, :total
                )
            """),
            {
                "tenant_id": tenant_id,
                "quotation_id": quotation_id,
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "discount": item["_discount"],
                "tax_rate": item.get("tax_rate", 0),
                "tax_amount": item["_tax"],
                "subtotal": item["_subtotal"],
                "total": item["_total"],
            },
        )

    await log_audit(
        db=db, tenant_id=tenant_id, user_id=user_id,
        action="quotation.create", entity_type="quotation",
        entity_id=quotation_id,
        description=f"Cotización creada: {folio}",
        ip_address=ip_address,
    )

    return {"id": quotation_id, "folio": folio, "total": total, "status": "active"}


async def get_quotation(db: AsyncSession, tenant_id: UUID, quotation_id: UUID) -> dict:
    result = await db.execute(
        text("""
            SELECT q.*, u.full_name as user_name, c.name as customer_name
            FROM quotations q
            JOIN users u ON u.id = q.user_id
            LEFT JOIN customers c ON c.id = q.customer_id
            WHERE q.id = :id AND q.tenant_id = :tenant_id
        """),
        {"id": quotation_id, "tenant_id": tenant_id},
    )
    q = result.fetchone()
    if not q:
        raise NotFoundException("Cotización no encontrada")

    q_dict = dict(q._mapping)

    items = await db.execute(
        text("""
            SELECT qi.*, p.name as product_name, p.product_code
            FROM quotation_items qi
            JOIN products p ON p.id = qi.product_id
            WHERE qi.quotation_id = :q_id AND qi.tenant_id = :tenant_id
        """),
        {"q_id": quotation_id, "tenant_id": tenant_id},
    )
    q_dict["items"] = [dict(row._mapping) for row in items.fetchall()]

    return q_dict


async def convert_to_sale(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    quotation_id: UUID,
    cash_register_id: UUID,
    location_id: UUID,
    payments: list | None = None,
    ip_address: str | None = None,
) -> dict:
    quotation = await db.execute(
        text("""
            SELECT * FROM quotations
            WHERE id = :id AND tenant_id = :tenant_id
            FOR UPDATE
        """),
        {"id": quotation_id, "tenant_id": tenant_id},
    )
    q = quotation.fetchone()
    if not q:
        raise NotFoundException("Cotización no encontrada")
    if q.status != "active":
        raise AppException(f"La cotización está en estado: {q.status}")
    if q.converted_to_sale_id:
        raise AppException("Esta cotización ya fue convertida a venta")

    items = await db.execute(
        text("""
            SELECT qi.*, p.track_inventory
            FROM quotation_items qi
            JOIN products p ON p.id = qi.product_id
            WHERE qi.quotation_id = :q_id AND qi.tenant_id = :tenant_id
        """),
        {"q_id": quotation_id, "tenant_id": tenant_id},
    )
    q_items = items.fetchall()
    if not q_items:
        raise AppException("La cotización no tiene productos")

    session_result = await db.execute(
        text("""
            SELECT id FROM cash_register_sessions
            WHERE cash_register_id = :cr_id
              AND tenant_id = :tenant_id
              AND closed_at IS NULL
            ORDER BY opened_at DESC
            LIMIT 1
        """),
        {"cr_id": cash_register_id, "tenant_id": tenant_id},
    )
    session = session_result.fetchone()
    if not session:
        raise AppException("No hay sesión activa de caja")

    sale_items = []
    for item in q_items:
        sale_items.append({
            "product_id": item.product_id,
            "location_id": location_id,
            "quantity": float(item.quantity),
            "unit_price": float(item.unit_price),
            "discount": float(item.discount),
            "tax_rate": float(item.tax_rate),
        })

    default_payments = payments or [{"payment_method": "cash", "amount": float(q.total), "currency": "MXN", "exchange_rate": 1.0}]

    sale = await create_sale(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        branch_id=q.branch_id,
        cash_register_id=cash_register_id,
        cash_register_session_id=session.id,
        customer_id=q.customer_id,
        items=sale_items,
        payments=default_payments,
        notes=f"Convertida de cotización {q.folio}",
        ip_address=ip_address,
    )

    await db.execute(
        text("""
            UPDATE quotations
            SET status = 'converted',
                converted_to_sale_id = :sale_id,
                updated_at = NOW()
            WHERE id = :id
        """),
        {"sale_id": sale["id"], "id": quotation_id},
    )

    await log_audit(
        db=db, tenant_id=tenant_id, user_id=user_id,
        action="quotation.convert", entity_type="quotation",
        entity_id=quotation_id,
        description=f"Cotización {q.folio} convertida a venta {sale['folio']}",
        ip_address=ip_address,
    )

    return {**sale, "quotation_folio": q.folio}


async def search_quotations(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    is_admin: bool = False,
) -> dict:
    conditions = ["tenant_id = :tenant_id"]
    params = {"tenant_id": tenant_id}

    if not is_admin and user_id:
        conditions.append("user_id = :user_id")
        params["user_id"] = user_id
    if status:
        conditions.append("status = :status")
        params["status"] = status

    where = " AND ".join(conditions)

    count = await db.execute(
        text(f"SELECT COUNT(*) FROM quotations WHERE {where}"), params,
    )
    total = count.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        text(f"""
            SELECT q.*, u.full_name as user_name, c.name as customer_name
            FROM quotations q
            JOIN users u ON u.id = q.user_id
            LEFT JOIN customers c ON c.id = q.customer_id
            WHERE {where}
            ORDER BY q.created_at DESC
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
