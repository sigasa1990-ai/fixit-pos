from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.audit import log_audit
from app.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException
from app.core.permissions import get_user_permissions
from app.core.security import (
    create_access_token,
    decode_access_token,
    validate_pin_format,
    verify_pin,
)
from app.core.tenant import set_session_context

settings = get_settings()


async def authenticate_user(
    db: AsyncSession,
    username: str,
    pin: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    if not validate_pin_format(pin):
        raise UnauthorizedException("Formato de PIN inválido")

    result = await db.execute(
        text("""
            SELECT u.id, u.tenant_id, u.role_id, u.pin_hash, u.full_name,
                   u.is_active, u.failed_login_attempts, u.locked_until,
                   r.role_type
            FROM users u
            JOIN roles r ON r.id = u.role_id
            WHERE u.username = :username
              AND u.tenant_id IS NOT NULL
        """),
        {"username": username},
    )
    user = result.fetchone()

    if not user:
        raise UnauthorizedException("Credenciales inválidas")

    if not user.is_active:
        raise ForbiddenException("Usuario inactivo")

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise ForbiddenException(
            "Usuario bloqueado temporalmente por demasiados intentos"
        )

    if not verify_pin(pin, user.pin_hash):
        await _handle_failed_login(db, user.id)
        raise UnauthorizedException("Credenciales inválidas")

    await db.execute(
        text("""
            UPDATE users
            SET failed_login_attempts = 0,
                locked_until = NULL,
                last_login_at = NOW(),
                last_login_ip = :ip
            WHERE id = :user_id
        """),
        {"user_id": user.id, "ip": ip_address},
    )

    permissions = await get_user_permissions(db, user.role_id)

    session_id = uuid4()
    session_token = uuid4()

    await db.execute(
        text("""
            INSERT INTO user_sessions (id, user_id, tenant_id, token_jti, ip_address, user_agent, logged_in_at, last_activity_at)
            VALUES (:id, :user_id, :tenant_id, :token_jti, :ip, :user_agent, NOW(), NOW())
        """),
        {
            "id": session_id,
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "token_jti": str(session_token),
            "ip": ip_address,
            "user_agent": user_agent,
        },
    )

    await set_session_context(db, user.tenant_id, user.id, user.role_type)

    await log_audit(
        db=db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="login",
        entity_type="user",
        entity_id=user.id,
        description=f"Login exitoso: {username}",
        ip_address=ip_address,
        user_agent=user_agent,
    )

    access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role_type,
        permissions=permissions,
        session_id=session_id,
    )

    return {
        "access_token": access_token,
        "user_id": str(user.id),
        "full_name": user.full_name,
        "role": user.role_type,
        "permissions": permissions,
        "tenant_id": str(user.tenant_id),
    }


async def _handle_failed_login(db: AsyncSession, user_id: UUID):
    result = await db.execute(
        text("""
            UPDATE users
            SET failed_login_attempts = failed_login_attempts + 1,
                locked_until = CASE
                    WHEN failed_login_attempts + 1 >= :max_attempts
                    THEN NOW() + INTERVAL '5 minutes'
                    ELSE locked_until
                END
            WHERE id = :user_id
            RETURNING failed_login_attempts
        """),
        {"user_id": user_id, "max_attempts": settings.MAX_LOGIN_ATTEMPTS},
    )


async def logout_user(
    db: AsyncSession,
    user_id: UUID,
    tenant_id: UUID,
    session_id: UUID,
    ip_address: str | None = None,
):
    await db.execute(
        text("""
            UPDATE user_sessions
            SET is_active = false, logged_out_at = NOW()
            WHERE id = :session_id AND user_id = :user_id AND tenant_id = :tenant_id
        """),
        {"session_id": session_id, "user_id": user_id, "tenant_id": tenant_id},
    )

    await log_audit(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="logout",
        description="Cierre de sesión",
        ip_address=ip_address,
    )
