from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    pin: str = Field(..., min_length=4, max_length=8)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    full_name: str
    role: str
    permissions: list[str]
    tenant_id: str
    branch_id: str | None = None
    cash_register_id: str | None = None


class LogoutResponse(BaseModel):
    message: str = "Sesión cerrada exitosamente"
