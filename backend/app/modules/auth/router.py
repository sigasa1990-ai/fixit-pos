from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_token_payload, get_current_tenant_id, get_current_user_id
from app.modules.auth.schemas import LoginRequest, LoginResponse, LogoutResponse
from app.modules.auth.service import authenticate_user, logout_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    result = await authenticate_user(
        db=db,
        username=body.username,
        pin=body.pin,
        ip_address=ip,
        user_agent=user_agent,
    )

    return LoginResponse(**result)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(get_current_token_payload),
    user_id=Depends(get_current_user_id),
    tenant_id=Depends(get_current_tenant_id),
):
    ip = request.client.host if request.client else None
    session_id = token_payload.get("session_id")

    await logout_user(
        db=db,
        user_id=user_id,
        tenant_id=tenant_id,
        session_id=session_id,
        ip_address=ip,
    )

    return LogoutResponse()


@router.get("/me")
async def get_current_user(
    request: Request,
    token_payload: dict = Depends(get_current_token_payload),
):
    return {
        "user_id": token_payload["sub"],
        "tenant_id": token_payload["tenant_id"],
        "role": token_payload["role"],
        "permissions": token_payload["permissions"],
    }
