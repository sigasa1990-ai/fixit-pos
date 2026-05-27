"""Multi-tenant isolation tests.

Verify that data from one tenant is not accessible by another tenant.
"""
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
    SEED_USER_ID,
    SEED_ROLE_ID,
    engine,
)

TENANT_A_ID = UUID("00000000-0000-0000-0000-000000000001")
TENANT_B_ID = UUID("00000002-0000-0000-0000-000000000001")


@pytest.fixture(autouse=True)
async def seed_tenant_b(engine):
    """Seed tenant B with its own data."""
    async with engine.begin() as conn:
        for table in [
            "audit_logs", "cash_register_movements", "payments", "sale_items",
            "sales", "quotation_items", "quotations", "inventory_movements",
            "inventory", "user_sessions", "users", "folio_controls",
            "cash_register_sessions", "cash_registers", "locations",
            "warehouses", "branches", "product_categories", "products",
            "role_permissions", "permissions", "roles", "tenants",
        ]:
            await conn.execute(text(f"DELETE FROM {table}"))

        # Tenant A
        await conn.execute(text("""
            INSERT INTO tenants (id, business_name, commercial_name, rfc)
            VALUES (:id, 'Tenant A', 'Tenant A', 'AAAA000000AAA')
        """), {"id": TENANT_A_ID})

        await conn.execute(text("""
            INSERT INTO branches (id, tenant_id, name)
            VALUES (:id, :tid, 'Branch A')
        """), {"id": UUID("00000000-0000-0000-0000-000000000010"), "tid": TENANT_A_ID})

        await conn.execute(text("""
            INSERT INTO roles (id, tenant_id, role_type, name)
            VALUES (:id, :tid, 'admin', 'Admin A')
        """), {"id": UUID("00000000-0000-0000-0000-000000000050"), "tid": TENANT_A_ID})

        # Tenant B
        await conn.execute(text("""
            INSERT INTO tenants (id, business_name, commercial_name, rfc)
            VALUES (:id, 'Tenant B', 'Tenant B', 'BBBB000000BBB')
        """), {"id": TENANT_B_ID})

        await conn.execute(text("""
            INSERT INTO branches (id, tenant_id, name)
            VALUES (:id, :tid, 'Branch B')
        """), {"id": UUID("00000002-0000-0000-0000-000000000010"), "tid": TENANT_B_ID})

        await conn.execute(text("""
            INSERT INTO roles (id, tenant_id, role_type, name)
            VALUES (:id, :tid, 'admin', 'Admin B')
        """), {"id": UUID("00000002-0000-0000-0000-000000000050"), "tid": TENANT_B_ID})

        # Add permissions for both
        for code in ['product.read', 'product.create']:
            await conn.execute(text("""
                INSERT INTO permissions (code, name, module)
                VALUES (:code, :code, :mod)
                ON CONFLICT (code) DO NOTHING
            """), {"code": code, "mod": code.split('.')[0]})

        perms = await conn.execute(text("SELECT id, code FROM permissions"))
        perms_rows = await perms.fetchall()
        for rid in [UUID("00000000-0000-0000-0000-000000000050"), UUID("00000002-0000-0000-0000-000000000050")]:
            for row in perms_rows:
                await conn.execute(text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (:rid, :pid)
                    ON CONFLICT DO NOTHING
                """), {"rid": rid, "pid": row.id})

        from app.core.security import hash_pin
        # User A
        await conn.execute(text("""
            INSERT INTO users (id, tenant_id, role_id, username, pin_hash, full_name, is_active)
            VALUES (:id, :tid, :rid, 'admin_a', :pin, 'Admin A', true)
        """), {
            "id": UUID("00000000-0000-0000-0000-000000000040"),
            "tid": TENANT_A_ID,
            "rid": UUID("00000000-0000-0000-0000-000000000050"),
            "pin": hash_pin("1234"),
        })

        # User B
        await conn.execute(text("""
            INSERT INTO users (id, tenant_id, role_id, username, pin_hash, full_name, is_active)
            VALUES (:id, :tid, :rid, 'admin_b', :pin, 'Admin B', true)
        """), {
            "id": UUID("00000002-0000-0000-0000-000000000040"),
            "tid": TENANT_B_ID,
            "rid": UUID("00000002-0000-0000-0000-000000000050"),
            "pin": hash_pin("5678"),
        })

        # Product A
        await conn.execute(text("""
            INSERT INTO products (id, tenant_id, product_code, name, price, cost)
            VALUES (:id, :tid, 'PRD-A', 'Producto A', 100, 50)
        """), {"id": UUID("00000000-0000-0000-0000-000000000060"), "tid": TENANT_A_ID})

        # Product B
        await conn.execute(text("""
            INSERT INTO products (id, tenant_id, product_code, name, price, cost)
            VALUES (:id, :tid, 'PRD-B', 'Producto B', 200, 100)
        """), {"id": UUID("00000002-0000-0000-0000-000000000060"), "tid": TENANT_B_ID})

    yield


class TestMultiTenant:
    async def test_tenant_a_cannot_see_tenant_b_products(self):
        """Tenant A should not see Tenant B's products."""
        async def login_and_search(tenant_id, username, pin):
            c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
            async with c as ac:
                resp = await ac.post("/api/v1/auth/login", json={
                    "username": username,
                    "pin": pin,
                })
                token = resp.json()["access_token"]

                search = await ac.get(
                    "/api/v1/products/search",
                    headers={"Authorization": f"Bearer {token}"},
                )
                return [p["name"] for p in search.json()["items"]]

        products_a = await login_and_search(TENANT_A_ID, "admin_a", "1234")
        products_b = await login_and_search(TENANT_B_ID, "admin_b", "5678")

        assert "Producto A" in products_a
        assert "Producto B" not in products_a
        assert "Producto B" in products_b
        assert "Producto A" not in products_b

    async def test_tenant_a_cannot_access_tenant_b_product_by_id(self):
        """Tenant A should get 404 when accessing Tenant B's product directly."""
        c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        async with c as ac:
            resp = await ac.post("/api/v1/auth/login", json={
                "username": "admin_a",
                "pin": "1234",
            })
            token = resp.json()["access_token"]

            product_b_id = UUID("00000002-0000-0000-0000-000000000060")
            resp2 = await ac.get(
                f"/api/v1/products/{product_b_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp2.status_code == 404

    async def test_tenant_login_cross_tenant_fails(self):
        """A user from Tenant A should not be able to login with Tenant B's credentials."""
        c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        async with c as ac:
            resp = await ac.post("/api/v1/auth/login", json={
                "username": "admin_a",
                "pin": "5678",
            })
            assert resp.status_code == 401
