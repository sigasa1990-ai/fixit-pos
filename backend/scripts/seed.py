"""Seed script: creates tenant, admin role, and admin user (admin/1234)."""
import asyncio
import os

import asyncpg
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SEED_TENANT_NAME = "FixIT Soluciones"
SEED_USERNAME = "admin"
SEED_PIN = "1234"
SEED_FULL_NAME = "Administrador"


async def seed():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL environment variable is required")

    conn = await asyncpg.connect(dsn)

    try:
        existing = await conn.fetchval("SELECT id FROM tenants WHERE business_name = $1", SEED_TENANT_NAME)
        if existing:
            print("Tenant already exists, skipping seed.")
            return

        tenant_id = await conn.fetchval(
            "INSERT INTO tenants (business_name, commercial_name, is_active) "
            "VALUES ($1, $2, true) RETURNING id",
            SEED_TENANT_NAME, SEED_TENANT_NAME,
        )
        print(f"Created tenant: {tenant_id}")

        role_id = await conn.fetchval(
            "INSERT INTO roles (tenant_id, name, role_type, description, is_system) "
            "VALUES ($1, 'Administrador', 'admin', 'Rol administrador del sistema', true) RETURNING id",
            tenant_id,
        )
        print(f"Created admin role: {role_id}")

        pin_hash = pwd_context.hash(SEED_PIN)
        user_id = await conn.fetchval(
            "INSERT INTO users (tenant_id, role_id, username, pin_hash, full_name, is_active) "
            "VALUES ($1, $2, $3, $4, $5, true) RETURNING id",
            tenant_id, role_id, SEED_USERNAME, pin_hash, SEED_FULL_NAME,
        )
        print(f"Created admin user: {user_id}")

        permission_ids = await conn.fetch(
            "SELECT id FROM permissions"
        )
        for row in permission_ids:
            await conn.execute(
                "INSERT INTO role_permissions (role_id, permission_id, tenant_id) VALUES ($1, $2, $3) "
                "ON CONFLICT (role_id, permission_id) DO NOTHING",
                role_id, row["id"], tenant_id,
            )
        print(f"Assigned {len(permission_ids)} permissions to admin role")

        branch_id = await conn.fetchval(
            "INSERT INTO branches (tenant_id, code, name, is_active) "
            "VALUES ($1, 'PRINCIPAL', 'Sucursal Principal', true) RETURNING id",
            tenant_id,
        )
        print(f"Created branch: {branch_id}")

        await conn.execute(
            "INSERT INTO user_branches (user_id, branch_id, tenant_id, is_default) "
            "VALUES ($1, $2, $3, true)",
            user_id, branch_id, tenant_id,
        )

        warehouse_id = await conn.fetchval(
            "INSERT INTO warehouses (tenant_id, branch_id, code, name, is_active) "
            "VALUES ($1, $2, 'PRINCIPAL', 'Almacen Principal', true) RETURNING id",
            tenant_id, branch_id,
        )
        print(f"Created warehouse: {warehouse_id}")

        location_id = await conn.fetchval(
            "INSERT INTO locations (tenant_id, warehouse_id, branch_id, code, name, is_active) "
            "VALUES ($1, $2, $3, 'PRINCIPAL', 'Ubicacion Principal', true) RETURNING id",
            tenant_id, warehouse_id, branch_id,
        )
        print(f"Created location: {location_id}")

        print("\nSeed completed successfully!")
        print(f"  Username: {SEED_USERNAME}")
        print(f"  PIN: {SEED_PIN}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
