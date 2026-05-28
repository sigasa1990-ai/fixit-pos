from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    try:
        return bcrypt.checkpw(plain_pin.encode("utf-8"), hashed_pin.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def validate_pin_format(pin: str) -> bool:
    if not pin or not pin.isdigit():
        return False
    return settings.PIN_MIN_LENGTH <= len(pin) <= settings.PIN_MAX_LENGTH


def create_access_token(
    user_id: UUID,
    tenant_id: UUID,
    role: str,
    permissions: list[str],
    session_id: UUID,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "permissions": permissions,
        "session_id": str(session_id),
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
