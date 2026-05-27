from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import AppException, InsufficientStockException, NotFoundException
from app.core.folios import generate_folio
from app.modules.cash_register.service import register_cash_movement


async def create_sale(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    branch_id: UUID,
    cash_register_id: UUID,
    cash_register_session_id: UUID,
    customer_id: UUID | None,
    items: list[dict],
    payments: list[dict],
    notes: str | None = None,
    ip_address: str | None = None,
) -> dict:
    # ================================================================
    # VALIDACIONES PREVIAS (dentro de la transacción)
    # ================================================================

    # 1. Validar caja abierta
    reg_result = await db.execute(
        text("""
            SELECT status, current_balance, branch_id FROM cash_registers
            WHERE id = :id AND tenant_id = :tenant_id
            FOR UPDATE
        """),
        {"id": cash_register_id, "tenant_id": tenant_id},
    )
    reg = reg_result.fetchone()
    if not reg:
        raise NotFoundException("Caja no encontrada")
    if reg.status != "open":
        raise AppException("La caja debe estar abierta para vender")

    # 2. Validar y reservar stock (FOR UPDATE locks)
    for item in items:
        stock_result = await db.execute(
            text("""
                SELECT i.quantity, p.name as product_name, p.cost
                FROM inventory i
                JOIN products p ON p.id = i.product_id
                WHERE i.tenant_id = :tenant_id
                  AND i.product_id = :product_id
                  AND i.location_id = :location_id
                FOR UPDATE
            """),
            {
                "tenant_id": tenant_id,
                "product_id": item["product_id"],
                "location_id": item["location_id"],
            },
        )
        stock = stock_result.fetchone()
        if not stock or float(stock.quantity) < item["quantity"]:
            pname = stock.product_name if stock else "Producto"
            raise InsufficientStockException(pname)
        item["_cost"] = float(stock.cost)

    # 3. Generar folio (atómico)
    folio = await generate_folio(db, tenant_id, branch_id, cash_register_id, "VTA")

    # ================================================================
    # CÁLCULOS
    # ================================================================
    subtotal = 0.0
    tax_total = 0.0
    discount_total = 0.0

    for item in items:
        line_subtotal = item["unit_price"] * item["quantity"]
        line_discount = item.get("discount", 0)
        line_after_discount = line_subtotal - line_discount
        line_tax = line_after_discount * (item.get("tax_rate", 0) / 100)
        line_total = line_after_discount + line_tax

        item["_subtotal"] = round(line_subtotal, 2)
        item["_discount"] = round(line_discount, 2)
        item["_tax"] = round(line_tax, 2)
        item["_total"] = round(line_total, 2)

        subtotal += line_subtotal
        discount_total += line_discount
        tax_total += line_tax

    total = round(subtotal - discount_total + tax_total, 2)

    # Validar que suma de pagos cubra el total
    total_paid = sum(p["amount"] for p in payments)
    if abs(total_paid - total) > 0.01:
        raise AppException(
            f"El total de pagos ({total_paid:,.2f}) no coincide con el total de la venta ({total:,.2f})"
        )

    # ================================================================
    # INSERTAR VENTA
    # ================================================================
    sale_result = await db.execute(
        text("""
            INSERT INTO sales (
                tenant_id, branch_id, cash_register_id, cash_register_session_id,
                user_id, customer_id, folio, status, subtotal, tax_total,
                discount_total, total, payment_status, notes
            ) VALUES (
                :tenant_id, :branch_id, :cash_register_id, :session_id,
                :user_id, :customer_id, :folio, 'completed', :subtotal,
                :tax_total, :discount_total, :total, 'paid', :notes
            )
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "branch_id": branch_id,
            "cash_register_id": cash_register_id,
            "session_id": cash_register_session_id,
            "user_id": user_id,
            "customer_id": customer_id,
            "folio": folio,
            "subtotal": round(subtotal, 2),
            "tax_total": round(tax_total, 2),
            "discount_total": round(discount_total, 2),
            "total": total,
            "notes": notes,
        },
    )
    sale_id = sale_result.scalar()

    # ================================================================
    # INSERTAR ITEMS + DESCONTAR INVENTARIO
    # ================================================================
    for item in items:
        await db.execute(
            text("""
                INSERT INTO sale_items (
                    tenant_id, sale_id, product_id, location_id,
                    quantity, unit_price, cost_price, discount,
                    tax_rate, tax_amount, subtotal, total
                ) VALUES (
                    :tenant_id, :sale_id, :product_id, :location_id,
                    :quantity, :unit_price, :cost_price, :discount,
                    :tax_rate, :tax_amount, :subtotal, :total
                )
            """),
            {
                "tenant_id": tenant_id,
                "sale_id": sale_id,
                "product_id": item["product_id"],
                "location_id": item["location_id"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "cost_price": item["_cost"],
                "discount": item["_discount"],
                "tax_rate": item.get("tax_rate", 0),
                "tax_amount": item["_tax"],
                "subtotal": item["_subtotal"],
                "total": item["_total"],
            },
        )

        # Descontar inventario
        await db.execute(
            text("""
                UPDATE inventory
                SET quantity = quantity - :quantity, updated_at = NOW()
                WHERE tenant_id = :tenant_id
                  AND product_id = :product_id
                  AND location_id = :location_id
            """),
            {
                "tenant_id": tenant_id,
                "product_id": item["product_id"],
                "location_id": item["location_id"],
                "quantity": item["quantity"],
            },
        )

        # Registrar movimiento de inventario
        await db.execute(
            text("""
                INSERT INTO inventory_movements (
                    tenant_id, product_id, warehouse_id, location_id, branch_id,
                    user_id, movement_type, reference_type, reference_id,
                    quantity_before, quantity_change, quantity_after
                )
                SELECT :tenant_id, :product_id, i.warehouse_id, i.location_id, i.branch_id,
                       :user_id, 'sale', 'sale', :sale_id,
                       i.quantity + :quantity, -:quantity, i.quantity
                FROM inventory i
                WHERE i.tenant_id = :tenant_id
                  AND i.product_id = :product_id
                  AND i.location_id = :location_id
            """),
            {
                "tenant_id": tenant_id,
                "product_id": item["product_id"],
                "location_id": item["location_id"],
                "user_id": user_id,
                "quantity": item["quantity"],
                "sale_id": sale_id,
            },
        )

    # ================================================================
    # REGISTRAR PAGOS
    # ================================================================
    total_cash = 0.0
    for payment in payments:
        amount_mxn = payment["amount"]
        if payment["currency"] == "USD":
            amount_mxn = round(payment["amount"] * payment["exchange_rate"], 2)

        if payment["payment_method"] == "cash":
            total_cash += amount_mxn

        await db.execute(
            text("""
                INSERT INTO payments (
                    tenant_id, sale_id, payment_method, currency, amount,
                    amount_mxn, exchange_rate, reference, bank,
                    authorization_code, last_four_digits, card_type
                ) VALUES (
                    :tenant_id, :sale_id, :method, :currency, :amount,
                    :amount_mxn, :exchange_rate, :reference, :bank,
                    :auth_code, :last_four, :card_type
                )
            """),
            {
                "tenant_id": tenant_id,
                "sale_id": sale_id,
                "method": payment["payment_method"],
                "currency": payment["currency"],
                "amount": payment["amount"],
                "amount_mxn": amount_mxn,
                "exchange_rate": payment.get("exchange_rate", 1.0),
                "reference": payment.get("reference"),
                "bank": payment.get("bank"),
                "auth_code": payment.get("authorization_code"),
                "last_four": payment.get("last_four_digits"),
                "card_type": payment.get("card_type"),
            },
        )

    # ================================================================
    # ACTUALIZAR SALDO CAJA (solo efectivo)
    # ================================================================
    if total_cash > 0:
        await register_cash_movement(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            cash_register_id=cash_register_id,
            amount=total_cash,
            movement_type="in",
            description=f"Venta {folio} - Efectivo",
            reference_type="sale",
            reference_id=sale_id,
            ip_address=ip_address,
        )

    # ================================================================
    # AUDITORÍA
    # ================================================================
    await log_audit(
        db=db, tenant_id=tenant_id, user_id=user_id,
        action="sale.create", entity_type="sale",
        entity_id=sale_id,
        description=f"Venta creada: {folio} - ${total:,.2f}",
        new_values={"folio": folio, "total": total, "items": len(items)},
        ip_address=ip_address,
    )

    return {
        "id": sale_id,
        "folio": folio,
        "total": total,
        "subtotal": round(subtotal, 2),
        "tax_total": round(tax_total, 2),
        "discount_total": round(discount_total, 2),
        "items_count": len(items),
        "status": "completed",
    }


async def get_sale(db: AsyncSession, tenant_id: UUID, sale_id: UUID) -> dict:
    result = await db.execute(
        text("""
            SELECT s.*, u.full_name as user_name,
                   c.name as customer_name
            FROM sales s
            JOIN users u ON u.id = s.user_id
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE s.id = :id AND s.tenant_id = :tenant_id
        """),
        {"id": sale_id, "tenant_id": tenant_id},
    )
    sale = result.fetchone()
    if not sale:
        raise NotFoundException("Venta no encontrada")

    sale_dict = dict(sale._mapping)

    items_result = await db.execute(
        text("""
            SELECT si.*, p.name as product_name, p.product_code
            FROM sale_items si
            JOIN products p ON p.id = si.product_id
            WHERE si.sale_id = :sale_id AND si.tenant_id = :tenant_id
        """),
        {"sale_id": sale_id, "tenant_id": tenant_id},
    )
    sale_dict["items"] = [dict(row._mapping) for row in items_result.fetchall()]

    payments_result = await db.execute(
        text("""
            SELECT * FROM payments
            WHERE sale_id = :sale_id AND tenant_id = :tenant_id
        """),
        {"sale_id": sale_id, "tenant_id": tenant_id},
    )
    sale_dict["payments"] = [dict(row._mapping) for row in payments_result.fetchall()]

    return sale_dict


async def search_sales(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID | None = None,
    branch_id: UUID | None = None,
    cash_register_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    folio: str | None = None,
    page: int = 1,
    page_size: int = 20,
    is_admin: bool = False,
) -> dict:
    conditions = ["s.tenant_id = :tenant_id"]
    params = {"tenant_id": tenant_id}

    if not is_admin and user_id:
        conditions.append("s.user_id = :user_id")
        params["user_id"] = user_id

    if branch_id:
        conditions.append("s.branch_id = :branch_id")
        params["branch_id"] = branch_id
    if cash_register_id:
        conditions.append("s.cash_register_id = :cr_id")
        params["cr_id"] = cash_register_id
    if date_from:
        conditions.append("s.created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("s.created_at <= :date_to")
        params["date_to"] = date_to
    if folio:
        conditions.append("s.folio ILIKE :folio")
        params["folio"] = f"%{folio}%"

    where = " AND ".join(conditions)

    count = await db.execute(
        text(f"SELECT COUNT(*) FROM sales s WHERE {where}"), params,
    )
    total = count.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        text(f"""
            SELECT s.*, u.full_name as user_name, c.name as customer_name
            FROM sales s
            JOIN users u ON u.id = s.user_id
            LEFT JOIN customers c ON c.id = s.customer_id
            WHERE {where}
            ORDER BY s.created_at DESC
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


async def cancel_sale(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    sale_id: UUID,
    reason: str,
    ip_address: str | None = None,
) -> dict:
    result = await db.execute(
        text("""
            SELECT * FROM sales
            WHERE id = :id AND tenant_id = :tenant_id
            FOR UPDATE
        """),
        {"id": sale_id, "tenant_id": tenant_id},
    )
    sale = result.fetchone()
    if not sale:
        raise NotFoundException("Venta no encontrada")
    if sale.status == "cancelled":
        raise AppException("La venta ya está cancelada")

    await db.execute(
        text("""
            UPDATE sales
            SET status = 'cancelled',
                payment_status = 'refunded',
                cancelled_at = NOW(),
                cancelled_by = :user_id,
                cancel_reason = :reason,
                updated_at = NOW()
            WHERE id = :id AND tenant_id = :tenant_id
        """),
        {"user_id": user_id, "reason": reason, "id": sale_id, "tenant_id": tenant_id},
    )

    # Revertir inventario
    items = await db.execute(
        text("""
            SELECT product_id, location_id, quantity FROM sale_items
            WHERE sale_id = :sale_id AND tenant_id = :tenant_id
        """),
        {"sale_id": sale_id, "tenant_id": tenant_id},
    )
    for item in items.fetchall():
        await db.execute(
            text("""
                UPDATE inventory
                SET quantity = quantity + :quantity, updated_at = NOW()
                WHERE tenant_id = :tenant_id
                  AND product_id = :product_id
                  AND location_id = :location_id
            """),
            {
                "tenant_id": tenant_id,
                "product_id": item.product_id,
                "location_id": item.location_id,
                "quantity": item.quantity,
            },
        )

    await log_audit(
        db=db, tenant_id=tenant_id, user_id=user_id,
        action="sale.cancel", entity_type="sale",
        entity_id=sale_id,
        description=f"Venta cancelada: {sale.folio} - Razón: {reason}",
        old_values={"status": sale.status, "payment_status": sale.payment_status},
        new_values={"status": "cancelled", "reason": reason},
        ip_address=ip_address,
    )

    return {"folio": sale.folio, "status": "cancelled", "reason": reason}
