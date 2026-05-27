from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.database import get_db
from app.dependencies import get_current_tenant_id, get_current_user_id
from app.modules.cash_register.schemas import (
    CashMovementRequest,
    CloseCashRegisterRequest,
    OpenCashRegisterRequest,
)
from app.modules.cash_register.service import (
    close_cash_register,
    get_cash_register,
    list_cash_registers,
    open_cash_register,
    register_cash_movement,
)

router = APIRouter(prefix="/api/v1/cash-registers", tags=["cash-registers"])


@router.get("")
async def api_list_cash_registers(
    branch_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("cashier.open")),
):
    import uuid
    return await list_cash_registers(
        db, tenant_id,
        branch_id=uuid.UUID(branch_id) if branch_id else None,
    )


@router.get("/{cash_register_id}")
async def api_get_cash_register(
    cash_register_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    _=Depends(require_permission("cashier.open")),
):
    import uuid
    return await get_cash_register(db, tenant_id, uuid.UUID(cash_register_id))


@router.post("/open")
async def api_open_cash_register(
    request: Request,
    body: OpenCashRegisterRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("cashier.open")),
):
    ip = request.client.host if request.client else None
    return await open_cash_register(
        db, tenant_id, user_id, body.cash_register_id,
        body.opening_balance, ip,
    )


@router.post("/close")
async def api_close_cash_register(
    request: Request,
    body: CloseCashRegisterRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("cashier.close")),
):
    ip = request.client.host if request.client else None
    return await close_cash_register(
        db, tenant_id, user_id, body.cash_register_id,
        body.notes, ip,
    )


@router.post("/movements")
async def api_cash_movement(
    request: Request,
    body: CashMovementRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
    user_id=Depends(get_current_user_id),
    _=Depends(require_permission("cashier.in")),
):
    ip = request.client.host if request.client else None
    return await register_cash_movement(
        db, tenant_id, user_id, body.cash_register_id,
        body.amount, body.movement_type, body.description,
        body.reference_type, body.reference_id, ip,
    )
