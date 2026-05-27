import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import (
    SEED_PRODUCT_ID,
    SEED_LOCATION_ID,
    SEED_WAREHOUSE_ID,
    SEED_BRANCH_ID,
    SEED_TENANT_ID,
)


class TestInventory:
    async def test_get_inventory(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/inventory", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["quantity"] == 100

    async def test_validate_stock_sufficient(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/inventory/validate-stock",
            headers=auth_headers,
            json={
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "location_id": str(SEED_LOCATION_ID),
                    "quantity": 10,
                }],
            },
        )
        assert response.status_code == 200
        assert response.json()[0]["available"] is True

    async def test_validate_stock_insufficient(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/inventory/validate-stock",
            headers=auth_headers,
            json={
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "location_id": str(SEED_LOCATION_ID),
                    "quantity": 9999,
                }],
            },
        )
        assert response.status_code == 409
        assert "insuficiente" in response.json()["detail"].lower()

    async def test_validate_stock_no_such_product(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/inventory/validate-stock",
            headers=auth_headers,
            json={
                "items": [{
                    "product_id": "00000000-0000-0000-0000-000000099999",
                    "location_id": str(SEED_LOCATION_ID),
                    "quantity": 1,
                }],
            },
        )
        assert response.status_code == 409

    async def test_transfer_stock(self, client: AsyncClient, auth_headers, engine):
        # Create destination location via engine
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO locations (id, tenant_id, warehouse_id, branch_id, name, code)
                    VALUES (:id, :tid, :wid, :bid, 'Almacen', 'ALM-001')
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": "00000000-0000-0000-0000-000000000021",
                    "tid": SEED_TENANT_ID,
                    "wid": SEED_WAREHOUSE_ID,
                    "bid": SEED_BRANCH_ID,
                },
            )
            await conn.execute(
                text("""
                    INSERT INTO inventory (tenant_id, product_id, location_id, warehouse_id, branch_id, quantity)
                    VALUES (:tid, :pid, :lid, :wid, :bid, 0)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "tid": SEED_TENANT_ID,
                    "pid": SEED_PRODUCT_ID,
                    "lid": "00000000-0000-0000-0000-000000000021",
                    "wid": SEED_WAREHOUSE_ID,
                    "bid": SEED_BRANCH_ID,
                },
            )

        response = await client.post(
            "/api/v1/inventory/transfer",
            headers=auth_headers,
            json={
                "product_id": str(SEED_PRODUCT_ID),
                "from_location_id": str(SEED_LOCATION_ID),
                "to_location_id": "00000000-0000-0000-0000-000000000021",
                "quantity": 10,
                "notes": "Test transfer",
            },
        )
        assert response.status_code == 200

    async def test_transfer_insufficient_stock(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/inventory/transfer",
            headers=auth_headers,
            json={
                "product_id": str(SEED_PRODUCT_ID),
                "from_location_id": str(SEED_LOCATION_ID),
                "to_location_id": str(SEED_LOCATION_ID),
                "quantity": 9999,
            },
        )
        assert response.status_code == 409

    async def test_adjust_stock(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/inventory/adjust",
            headers=auth_headers,
            json={
                "product_id": str(SEED_PRODUCT_ID),
                "location_id": str(SEED_LOCATION_ID),
                "new_quantity": 200,
                "reason": "Inventory count adjustment",
            },
        )
        assert response.status_code == 200

        inv = await client.get("/api/v1/inventory", headers=auth_headers)
        item = next(i for i in inv.json() if i["product_id"] == str(SEED_PRODUCT_ID))
        assert item["quantity"] == 200
