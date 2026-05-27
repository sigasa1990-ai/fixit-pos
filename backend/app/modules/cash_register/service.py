from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.exceptions import AppException, NotFoundException


async def list_cash_registers(
    db: AsyncSession,
    tenant_id: UUID,
    branch_id: UUID | None = None,
) -> list[dict]:
    conditions = ["cr.tenant_id = :tenant_id"]
    params = {"tenant_id": tenant_id}
    if branch_id:
        conditions.append("cr.branch_id = :branch_id")
        params["branch_id"] = branch_id

    where = " AND ".join(conditions)
    result = await db.execute(
        text(f"""
            SELECT cr.*, b.name as branch_name, l.name as location_name
            FROM cash_registers cr
            JOIN branches b ON b.id = cr.branch_id
            JOIN locations l ON l.id = cr.location_id
            WHERE {where}
            ORDER BY cr.name
        """),
        params,
    )
    return [dict(row._mapping) for row in result.fetchall()]


async def get_cash_register(
    db: AsyncSession,
    tenant_id: UUID,
    cash_register_id: UUID,
) -> dict:
    result = await db.execute(
        text("""
            SELECT cr.*, b.name as branch_name, l.name as location_name
            FROM cash_registers cr
            JOIN branches b ON b.id = cr.branch_id
            JOIN locations l ON l.id = cr.location_id
            WHERE cr.id = :id AND cr.tenant_id = :tenant_id
        """),
        {"id": cash_register_id, "tenant_id": tenant_id},
    )
    row = result.fetchone()
    if not row:
        raise NotFoundException("Caja no encontrada")
    return dict(row._mapping)


async def open_cash_register(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    cash_register_id: UUID,
    opening_balance: float,
    ip_address: str | None = None,
) -> dict:
    # Lock row to prevent race condition
    lock_result = await db.execute(
        text("""
            SELECT status, name, branch_id, current_balance, opening_balance
            FROM cash_registers
            WHERE id = :id AND tenant_id = :tenant_id
            FOR UPDATE
        """),
        {"id": cash_register_id, "tenant_id": tenant_id},
    )
    reg = lock_result.fetchone()
    if not reg:
        raise NotFoundException("Caja no encontrada")
    reg = {"status": reg.status, "name": reg.name, "branch_id": reg.branch_id,
           "current_balance": reg.current_balance, "opening_balance": reg.opening_balance}
    if reg["status"] == "open":
        raise AppException("La caja ya está abierta")

    now = datetime.now(timezone.utc)

    await db.execute(
        text("""
            UPDATE cash_registers
            SET status = 'open',
                current_balance = :balance,
                opening_balance = :balance,
                opened_by = :user_id,
                closed_by = NULL,
                closed_at = NULL,
                updated_at = NOW()
            WHERE id = :id AND tenant_id = :tenant_id
        """),
        {
            "balance": opening_balance,
            "user_id": user_id,
            "id": cash_register_id,
            "tenant_id": tenant_id,
        },
    )

    session_result = await db.execute(
        text("""
            INSERT INTO cash_register_sessions (
                tenant_id, cash_register_id, branch_id,
                opened_by, opening_balance, opened_at
            ) VALUES (
                :tenant_id, :cash_register_id, :branch_id,
                :opened_by, :opening_balance, :opened_at
            )
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "cash_register_id": cash_register_id,
            "branch_id": reg["branch_id"],
            "opened_by": user_id,
            "opening_balance": opening_balance,
            "opened_at": now,
        },
    )
    session_id = session_result.scalar()

    await log_audit(
        db=db, tenant_id=tenant_id, user_id=user_id,
        action="cashier.open", entity_type="cash_register",
        entity_id=cash_register_id,
        description=f"Caja abierta: {reg['name']} (${opening_balance:,.2f})",
        new_values={"opening_balance": opening_balance},
        ip_address=ip_address,
    )

    return {"session_id": session_id, "status": "open", "balance": opening_balance}


async def close_cash_register(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    cash_register_id: UUID,
    notes: str | None = None,
    ip_address: str | None = None,
) -> dict:
    # Lock row to prevent race condition
    lock_result = await db.execute(
        text("""
            SELECT status, name, branch_id, current_balance, opening_balance
            FROM cash_registers
            WHERE id = :id AND tenant_id = :tenant_id
            FOR UPDATE
        """),
        {"id": cash_register_id, "tenant_id": tenant_id},
    )
    reg = lock_result.fetchone()
    if not reg:
        raise NotFoundException("Caja no encontrada")
    reg = {"status": reg.status, "name": reg.name, "branch_id": reg.branch_id,
           "current_balance": reg.current_balance, "opening_balance": reg.opening_balance}
    if reg["status"] != "open":
        raise AppException("La caja no está abierta")

    result = await db.execute(
        text("""
            SELECT id, opening_balance, opening_balance as ob
            FROM cash_register_sessions
            WHERE cash_register_id = :cr_id
              AND tenant_id = :tenant_id
              AND closed_at IS NULL
            ORDER BY opened_at DESC
            LIMIT 1
        """),
        {"cr_id": cash_register_id, "tenant_id": tenant_id},
    )
    session = result.fetchone()
    if not session:
        raise AppException("No se encontró sesión activa de caja")

    current_balance = reg["current_balance"]
    session_opening = reg["opening_balance"]

    sales_totals = await db.execute(
        text("""
            SELECT
                COUNT(*) as sale_count,
                COALESCE(SUM(total), 0) as total_sales,
                COALESCE(SUM(CASE WHEN pm.payment_method = 'cash' THEN pm.amount_mxn ELSE 0 END), 0) as cash_total,
                COALESCE(SUM(CASE WHEN pm.payment_method = 'card' THEN pm.amount_mxn ELSE 0 END), 0) as card_total,
                COALESCE(SUM(CASE WHEN pm.payment_method = 'transfer' THEN pm.amount_mxn ELSE 0 END), 0) as transfer_total,
                COALESCE(SUM(CASE WHEN pm.payment_method = 'usd' THEN pm.amount_mxn ELSE 0 END), 0) as usd_total
            FROM sales s
            LEFT JOIN payments pm ON pm.sale_id = s.id
            WHERE s.cash_register_session_id = :session_id
              AND s.tenant_id = :tenant_id
              AND s.status = 'completed'
        """),
        {"session_id": session.id, "tenant_id": tenant_id},
    )
    totals = sales_totals.fetchone()

    cash_movements = await db.execute(
        text("""
            SELECT
                COALESCE(SUM(CASE WHEN movement_type = 'in' THEN amount ELSE 0 END), 0) as total_in,
                COALESCE(SUM(CASE WHEN movement_type = 'out' THEN amount ELSE 0 END), 0) as total_out
            FROM cash_register_movements
            WHERE cash_register_session_id = :session_id
              AND tenant_id = :tenant_id
        """),
        {"session_id": session.id, "tenant_id": tenant_id},
    )
    mov = cash_movements.fetchone()

    expected_balance = (
        session_opening
        + float(totals.cash_total)
        + float(mov.total_in)
        - float(mov.total_out)
    )
    difference = current_balance - expected_balance

    await db.execute(
        text("""
            UPDATE cash_register_sessions
            SET closed_by = :user_id,
                closing_balance = :closing_balance,
                expected_balance = :expected_balance,
                difference = :difference,
                total_cash_sales = :cash_sales,
                total_card_sales = :card_sales,
                total_transfer_sales = :transfer_sales,
                total_usd_sales = :usd_sales,
                total_cash_in = :cash_in,
                total_cash_out = :cash_out,
                total_sales_count = :sale_count,
                closed_at = NOW(),
                notes = :notes
            WHERE id = :id
        """),
        {
            "user_id": user_id,
            "closing_balance": current_balance,
            "expected_balance": expected_balance,
            "difference": difference,
            "cash_sales": float(totals.cash_total),
            "card_sales": float(totals.card_total),
            "transfer_sales": float(totals.transfer_total),
            "usd_sales": float(totals.usd_total),
            "cash_in": float(mov.total_in),
            "cash_out": float(mov.total_out),
            "sale_count": totals.sale_count,
            "notes": notes,
            "id": session.id,
        },
    )

    await db.execute(
        text("""
            UPDATE cash_registers
            SET status = 'closed',
                closed_by = :user_id,
                closed_at = NOW(),
                updated_at = NOW()
            WHERE id = :id AND tenant_id = :tenant_id
        """),
        {"user_id": user_id, "id": cash_register_id, "tenant_id": tenant_id},
    )

    await log_audit(
        db=db, tenant_id=tenant_id, user_id=user_id,
        action="cashier.close", entity_type="cash_register",
        entity_id=cash_register_id,
        description=f"Caja cerrada. Esperado: ${expected_balance:,.2f}, Real: ${current_balance:,.2f}, Diferencia: ${difference:,.2f}",
        new_values={"closing_balance": current_balance, "expected": expected_balance, "difference": difference},
        ip_address=ip_address,
    )

    return {
        "session_id": session.id,
        "status": "closed",
        "closing_balance": current_balance,
        "expected_balance": expected_balance,
        "difference": difference,
        "total_sales": float(totals.total_sales),
        "sale_count": totals.sale_count,
    }


async def register_cash_movement(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    cash_register_id: UUID,
    amount: float,
    movement_type: str,
    description: str,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    ip_address: str | None = None,
) -> dict:
    # Lock row to prevent race condition
    lock_result = await db.execute(
        text("""
            SELECT status, name, branch_id, current_balance, opening_balance
            FROM cash_registers
            WHERE id = :id AND tenant_id = :tenant_id
            FOR UPDATE
        """),
        {"id": cash_register_id, "tenant_id": tenant_id},
    )
    reg = lock_result.fetchone()
    if not reg:
        raise NotFoundException("Caja no encontrada")
    reg = {"status": reg.status, "name": reg.name, "branch_id": reg.branch_id,
           "current_balance": reg.current_balance, "opening_balance": reg.opening_balance}
    if reg["status"] != "open":
        raise AppException("La caja debe estar abierta")

    result = await db.execute(
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
    session = result.fetchone()
    if not session:
        raise AppException("No hay sesión activa de caja")

    balance_before = float(reg["current_balance"])
    balance_after = balance_before + (amount if movement_type == "in" else -amount)

    await db.execute(
        text("""
            UPDATE cash_registers
            SET current_balance = :new_balance, updated_at = NOW()
            WHERE id = :id AND tenant_id = :tenant_id
        """),
        {"new_balance": balance_after, "id": cash_register_id, "tenant_id": tenant_id},
    )

    mov_result = await db.execute(
        text("""
            INSERT INTO cash_register_movements (
                tenant_id, cash_register_id, cash_register_session_id, branch_id,
                user_id, movement_type, amount, balance_before, balance_after,
                reference_type, reference_id, description
            ) VALUES (
                :tenant_id, :cr_id, :session_id, :branch_id,
                :user_id, :movement_type, :amount, :balance_before, :balance_after,
                :ref_type, :ref_id, :description
            )
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "cr_id": cash_register_id,
            "session_id": session.id,
            "branch_id": reg["branch_id"],
            "user_id": user_id,
            "movement_type": movement_type,
            "amount": amount,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "ref_type": reference_type,
            "ref_id": reference_id,
            "description": description,
        },
    )
    mov_id = mov_result.scalar()

    audit_action = "cashier.in" if movement_type == "in" else "cashier.out"
    await log_audit(
        db=db, tenant_id=tenant_id, user_id=user_id,
        action=audit_action, entity_type="cash_register_movement",
        entity_id=mov_id, description=description,
        new_values={"amount": amount, "balance_before": balance_before, "balance_after": balance_after},
        ip_address=ip_address,
    )

    return {"movement_id": mov_id, "balance_before": balance_before, "balance_after": balance_after}
