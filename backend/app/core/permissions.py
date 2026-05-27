from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException
from app.database import get_db


class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    async def __call__(self, request: Request, db: AsyncSession = Depends(get_db)):
        token_payload = getattr(request.state, "token_payload", None)
        if not token_payload:
            raise ForbiddenException("No autenticado")

        permissions = token_payload.get("permissions", [])

        if self.required_permission not in permissions:
            raise ForbiddenException(
                f"Permiso requerido: {self.required_permission}"
            )
        return True


def require_permission(permission: str) -> PermissionChecker:
    return PermissionChecker(permission)


def has_permission(token_payload: dict, permission: str) -> bool:
    return permission in token_payload.get("permissions", [])


async def get_user_permissions(
    db: AsyncSession,
    role_id: UUID,
) -> list[str]:
    query = text("""
        SELECT p.code
        FROM role_permissions rp
        JOIN permissions p ON p.id = rp.permission_id
        WHERE rp.role_id = :role_id
    """)
    result = await db.execute(query, {"role_id": role_id})
    return [row[0] for row in result.fetchall()]
