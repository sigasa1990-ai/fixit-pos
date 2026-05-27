import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database import get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://fixit:fixit@localhost:5432/fixit_pos_test"

settings = get_settings()
original_db_url = settings.DATABASE_URL


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    import os
    import subprocess

    # Create test database if not exists
    try:
        conn = await asyncpg.connect(
            host="localhost",
            user="fixit",
            password="fixit",
            database="postgres",
        )
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'fixit_pos_test'"
        )
        if not exists:
            await conn.execute("CREATE DATABASE fixit_pos_test")
        await conn.close()
    except Exception:
        pytest.skip("No PostgreSQL available")

    # Run schema
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql")
    if os.path.exists(schema_path):
        result = subprocess.run(
            ["psql", "-U", "fixit", "-d", "fixit_pos_test", "-f", schema_path],
            capture_output=True, text=True, timeout=30,
        )

    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_size=5)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as s:
        await s.execute(text("SET app.tenant_id = 'seed-tenant-id'"))
        yield s
        await s.rollback()


# Seed data IDs
SEED_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
SEED_BRANCH_ID = UUID("00000000-0000-0000-0000-000000000010")
SEED_LOCATION_ID = UUID("00000000-0000-0000-0000-000000000020")
SEED_CASH_REGISTER_ID = UUID("00000000-0000-0000-0000-000000000030")
SEED_USER_ID = UUID("00000000-0000-0000-0000-000000000040")
SEED_ROLE_ID = UUID("00000000-0000-0000-0000-000000000050")
SEED_PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000060")
SEED_CATEGORY_ID = UUID("00000000-0000-0000-0000-000000000070")
SEED_WAREHOUSE_ID = UUID("00000000-0000-0000-0000-000000000080")
SEED_CUSTOMER_ID = UUID("00000000-0000-0000-0000-000000000090")
SEED_FOLIO_CONTROL_ID = UUID("00000000-0000-0000-0000-000000000100")


def override_get_db():
    async def _get_db():
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with session_factory() as s:
            await s.execute(text("SET app.tenant_id = :tid"), {"tid": str(SEED_TENANT_ID)})
            yield s
            await s.rollback()
    return _get_db


@pytest_asyncio.fixture(autouse=True)
async def seed_data(engine):
    async with engine.begin() as conn:
        # Clean all tables
        for table in [
            "audit_logs", "cash_register_movements", "payments", "sale_items",
            "sales", "quotation_items", "quotations", "inventory_movements",
            "inventory", "user_sessions", "users", "folio_controls",
            "cash_register_sessions", "cash_registers", "locations",
            "warehouses", "branches", "product_categories", "products",
            "role_permissions", "permissions", "roles", "tenants",
        ]:
            await conn.execute(text(f"DELETE FROM {table}"))

        await conn.execute(text("""
            INSERT INTO tenants (id, business_name, commercial_name, rfc)
            VALUES (:id, 'Test Business', 'Test', 'XAXX010101000')
        """), {"id": SEED_TENANT_ID})

        await conn.execute(text("""
            INSERT INTO branches (id, tenant_id, name, address)
            VALUES (:id, :tid, 'Sucursal Principal', 'Test Address')
        """), {"id": SEED_BRANCH_ID, "tid": SEED_TENANT_ID})

        await conn.execute(text("""
            INSERT INTO warehouses (id, tenant_id, branch_id, name)
            VALUES (:id, :tid, :bid, 'Almacen Principal')
        """), {"id": SEED_WAREHOUSE_ID, "tid": SEED_TENANT_ID, "bid": SEED_BRANCH_ID})

        await conn.execute(text("""
            INSERT INTO locations (id, tenant_id, warehouse_id, branch_id, name, code)
            VALUES (:id, :tid, :wid, :bid, 'Mostrador', 'MTR-001')
        """), {"id": SEED_LOCATION_ID, "tid": SEED_TENANT_ID, "wid": SEED_WAREHOUSE_ID, "bid": SEED_BRANCH_ID})

        await conn.execute(text("""
            INSERT INTO cash_registers (id, tenant_id, branch_id, location_id, code, name, status)
            VALUES (:id, :tid, :bid, :lid, 'CAJ-001', 'Caja Principal', 'closed')
        """), {"id": SEED_CASH_REGISTER_ID, "tid": SEED_TENANT_ID, "bid": SEED_BRANCH_ID, "lid": SEED_LOCATION_ID})

        await conn.execute(text("""
            INSERT INTO product_categories (id, tenant_id, name)
            VALUES (:id, :tid, 'General')
        """), {"id": SEED_CATEGORY_ID, "tid": SEED_TENANT_ID})

        await conn.execute(text("""
            INSERT INTO products (id, tenant_id, category_id, product_code, name, price, cost, tax_rate)
            VALUES (:id, :tid, :cid, 'PRD-000001', 'Producto de Prueba', 100.00, 50.00, 16.00)
        """), {"id": SEED_PRODUCT_ID, "tid": SEED_TENANT_ID, "cid": SEED_CATEGORY_ID})

        await conn.execute(text("""
            INSERT INTO inventory (tenant_id, product_id, location_id, warehouse_id, branch_id, quantity, min_stock)
            VALUES (:tid, :pid, :lid, :wid, :bid, 100, 5)
        """), {"tid": SEED_TENANT_ID, "pid": SEED_PRODUCT_ID, "lid": SEED_LOCATION_ID, "wid": SEED_WAREHOUSE_ID, "bid": SEED_BRANCH_ID})

        await conn.execute(text("""
            INSERT INTO roles (id, tenant_id, role_type, name, description)
            VALUES (:id, :tid, 'admin', 'Administrador', 'Full access')
        """), {"id": SEED_ROLE_ID, "tid": SEED_TENANT_ID})

        # Add permissions
        perm_codes = [
            'product.create', 'product.read', 'product.update',
            'inventory.read', 'inventory.transfer', 'inventory.adjust',
            'customer.create', 'customer.read', 'customer.update',
            'cashier.open', 'cashier.close', 'cashier.in',
            'sale.create', 'sale.read', 'sale.cancel', 'sale.read_global',
            'quotation.create', 'quotation.read', 'quotation.convert',
        ]
        for code in perm_codes:
            await conn.execute(text("""
                INSERT INTO permissions (code, name, module)
                VALUES (:code, :code, :mod)
                ON CONFLICT (code) DO NOTHING
            """), {"code": code, "mod": code.split('.')[0]})

        # Assign all permissions to admin role
        perms = await conn.execute(text("SELECT id, code FROM permissions"))
        for row in await perms.fetchall():
            await conn.execute(text("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (:rid, :pid)
                ON CONFLICT DO NOTHING
            """), {"rid": SEED_ROLE_ID, "pid": row.id})

        # Create admin user
        from app.core.security import hash_pin
        from app.core.folios import ensure_folio_control_exists

        await conn.execute(text("""
            INSERT INTO users (id, tenant_id, role_id, username, pin_hash, full_name, is_active)
            VALUES (:id, :tid, :rid, 'admin', :pin, 'Admin Test', true)
        """), {"id": SEED_USER_ID, "tid": SEED_TENANT_ID, "rid": SEED_ROLE_ID, "pin": hash_pin("1234")})

        # Folio control
        await conn.execute(text("""
            INSERT INTO folio_controls (id, tenant_id, branch_id, cash_register_id, document_type, prefix, next_number)
            VALUES (:id, :tid, :bid, :crid, 'VTA', 'VTA-', 1)
        """), {"id": SEED_FOLIO_CONTROL_ID, "tid": SEED_TENANT_ID, "bid": SEED_BRANCH_ID, "crid": SEED_CASH_REGISTER_ID})

    yield


@pytest_asyncio.fixture
async def client(engine, seed_data):
    app.dependency_overrides[get_db] = override_get_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(client):
    response = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "pin": "1234",
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
