"""Concurrency and race condition tests.

These tests verify that the system handles concurrent operations correctly,
preventing race conditions in critical paths like:
- Opening/closing cash registers
- Folio generation (must be unique)
- Inventory deduction (no negative stock)
- Sale creation (atomic transaction consistency)
"""
import asyncio
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import get_db
from app.main import app
from tests.conftest import (
    SEED_BRANCH_ID,
    SEED_CASH_REGISTER_ID,
    SEED_LOCATION_ID,
    SEED_PRODUCT_ID,
    SEED_TENANT_ID,
    SEED_USER_ID,
    engine,
)


async def _get_admin_token(client: AsyncClient) -> str:
    response = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "pin": "1234",
    })
    return response.json()["access_token"]


async def _open_register(client: AsyncClient, headers: dict):
    await client.post(
        "/api/v1/cash-registers/open",
        headers=headers,
        json={
            "cash_register_id": str(SEED_CASH_REGISTER_ID),
            "opening_balance": 1000.00,
        },
    )


class TestConcurrency:
    """Race condition tests that simulate concurrent operations."""

    async def test_concurrent_folio_uniqueness(self, client: AsyncClient, auth_headers):
        """Verify that concurrent sale creations generate unique folios."""
        await _open_register(client, auth_headers)

        async def create_sale(n: int) -> str:
            c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
            async with c as ac:
                ac.headers.update(auth_headers)
                resp = await ac.post("/api/v1/sales", json={
                    "branch_id": str(SEED_BRANCH_ID),
                    "cash_register_id": str(SEED_CASH_REGISTER_ID),
                    "items": [{
                        "product_id": str(SEED_PRODUCT_ID),
                        "location_id": str(SEED_LOCATION_ID),
                        "quantity": 1,
                        "unit_price": 100.00,
                        "tax_rate": 16.00,
                    }],
                    "payments": [{
                        "payment_method": "cash",
                        "amount": 116.00,
                        "currency": "MXN",
                    }],
                })
                if resp.status_code == 200:
                    return resp.json()["folio"]
                return None

        tasks = [create_sale(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        folios = [r for r in results if r is not None]

        assert len(folios) == 10
        assert len(set(folios)) == 10, "Duplicate folios detected!"

    async def test_concurrent_stock_integrity(self, client: AsyncClient, auth_headers):
        """Verify that concurrent sales don't cause negative stock."""
        await _open_register(client, auth_headers)

        # Reset stock
        async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as s:
            await s.execute(
                text("""
                    UPDATE inventory SET quantity = 5
                    WHERE tenant_id = :tid AND product_id = :pid
                """),
                {"tid": SEED_TENANT_ID, "pid": SEED_PRODUCT_ID},
            )
            await s.commit()

        async def sell_one(n: int) -> bool:
            c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
            async with c as ac:
                ac.headers.update(auth_headers)
                resp = await ac.post("/api/v1/sales", json={
                    "branch_id": str(SEED_BRANCH_ID),
                    "cash_register_id": str(SEED_CASH_REGISTER_ID),
                    "items": [{
                        "product_id": str(SEED_PRODUCT_ID),
                        "location_id": str(SEED_LOCATION_ID),
                        "quantity": 2,
                        "unit_price": 100.00,
                        "tax_rate": 16.00,
                    }],
                    "payments": [{
                        "payment_method": "cash",
                        "amount": 232.00,
                        "currency": "MXN",
                    }],
                })
                return resp.status_code == 200

        # Try to sell 4 * 2 = 8 units, but only 5 available
        tasks = [sell_one(i) for i in range(4)]
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for r in results if r)

        assert success_count <= 2, "Should not allow more sales than available stock"
        assert success_count >= 1, "At least one sale should succeed"

        # Verify no negative stock
        async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as s:
            result = await s.execute(
                text("""
                    SELECT quantity FROM inventory
                    WHERE tenant_id = :tid AND product_id = :pid
                """),
                {"tid": SEED_TENANT_ID, "pid": SEED_PRODUCT_ID},
            )
            remaining = result.scalar()
            await s.commit()

        assert remaining >= 0, f"Stock went negative! ({remaining})"

    async def test_concurrent_cash_register_open(self, client: AsyncClient):
        """Verify that only one open operation succeeds concurrently."""
        token1 = await _get_admin_token(client)
        token2 = await _get_admin_token(client)
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Close if already open
        for h in [headers1]:
            await client.post(
                "/api/v1/cash-registers/close",
                headers=h,
                json={"cash_register_id": str(SEED_CASH_REGISTER_ID)},
            )

        async def open_reg(h: dict) -> int:
            c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
            async with c as ac:
                ac.headers.update(h)
                resp = await ac.post("/api/v1/cash-registers/open", json={
                    "cash_register_id": str(SEED_CASH_REGISTER_ID),
                    "opening_balance": 500.00,
                })
                return resp.status_code

        results = await asyncio.gather(open_reg(headers1), open_reg(headers2))
        success = sum(1 for r in results if r == 200)
        assert success == 1, f"Expected exactly 1 open to succeed, got {success}"

    async def test_cancel_sale_concurrent(self, client: AsyncClient, auth_headers):
        """Verify that cancelling a sale twice concurrently is safe."""
        await _open_register(client, auth_headers)

        resp = await client.post("/api/v1/sales", json={
            "branch_id": str(SEED_BRANCH_ID),
            "cash_register_id": str(SEED_CASH_REGISTER_ID),
            "items": [{
                "product_id": str(SEED_PRODUCT_ID),
                "location_id": str(SEED_LOCATION_ID),
                "quantity": 1,
                "unit_price": 100.00,
                "tax_rate": 16.00,
            }],
            "payments": [{
                "payment_method": "cash",
                "amount": 116.00,
                "currency": "MXN",
            }],
        })
        sale_id = resp.json()["id"]

        async def cancel_sale(h: dict) -> int:
            c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
            async with c as ac:
                ac.headers.update(h)
                resp2 = await ac.post(f"/api/v1/sales/{sale_id}/cancel", json={
                    "reason": "Concurrent cancel test",
                })
                return resp2.status_code

        t1 = await _get_admin_token(client)
        t2 = await _get_admin_token(client)
        results = await asyncio.gather(
            cancel_sale({"Authorization": f"Bearer {t1}"}),
            cancel_sale({"Authorization": f"Bearer {t2}"}),
        )

        success = sum(1 for r in results if r == 200)
        assert success == 1, f"Expected exactly 1 cancel to succeed, got {success}"
