import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


async def idempotency_middleware(
    request: Request,
    call_next: Callable,
    db: AsyncSession,
    idempotency_key: str,
    tenant_id: UUID,
    resource_type: str,
) -> Response:
    request_hash = hashlib.sha256(
        json.dumps(
            {"method": request.method, "path": request.url.path, "body": await request.body()},
            default=str,
        ).encode()
    ).hexdigest()

    # Check for existing result
    existing = await db.execute(
        text("""
            SELECT response_status, response_body
            FROM idempotency_keys
            WHERE tenant_id = :tenant_id
              AND idempotency_key = :key
              AND resource_type = :resource_type
              AND expires_at > NOW()
        """),
        {"tenant_id": tenant_id, "key": idempotency_key, "resource_type": resource_type},
    )
    row = existing.fetchone()
    if row:
        return Response(
            content=row.response_body,
            status_code=row.response_status,
            media_type="application/json",
        )

    # Process request
    response = await call_next(request)

    # Store result
    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    await db.execute(
        text("""
            INSERT INTO idempotency_keys (
                tenant_id, idempotency_key, resource_type,
                resource_id, request_hash, response_status, response_body, expires_at
            ) VALUES (
                :tenant_id, :key, :resource_type,
                :resource_id, :request_hash, :status, :body,
                :expires_at
            )
            ON CONFLICT (tenant_id, idempotency_key)
            DO UPDATE SET
                response_status = EXCLUDED.response_status,
                response_body = EXCLUDED.response_body
        """),
        {
            "tenant_id": tenant_id,
            "key": idempotency_key,
            "resource_type": resource_type,
            "resource_id": None,
            "request_hash": request_hash,
            "status": response.status_code,
            "body": response_body.decode(),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        },
    )
    await db.commit()

    return Response(
        content=response_body,
        status_code=response.status_code,
        media_type="application/json",
        headers=dict(response.headers),
    )


async def get_idempotency_key(
    x_idempotency_key: str | None = Header(None),
) -> str | None:
    return x_idempotency_key
