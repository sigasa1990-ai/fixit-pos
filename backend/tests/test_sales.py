import pytest
from httpx import AsyncClient

from tests.conftest import (
    SEED_BRANCH_ID,
    SEED_CASH_REGISTER_ID,
    SEED_LOCATION_ID,
    SEED_PRODUCT_ID,
)


@pytest.fixture(autouse=True)
async def open_register(client: AsyncClient, auth_headers):
    """Ensure cash register is open for sales tests"""
    await client.post(
        "/api/v1/cash-registers/open",
        headers=auth_headers,
        json={
            "cash_register_id": str(SEED_CASH_REGISTER_ID),
            "opening_balance": 1000.00,
        },
    )
    yield
    # Close after tests
    await client.post(
        "/api/v1/cash-registers/close",
        headers=auth_headers,
        json={
            "cash_register_id": str(SEED_CASH_REGISTER_ID),
        },
    )


class TestSales:
    async def test_create_sale_cash(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
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
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["folio"].startswith("VTA-")
        assert data["items_count"] == 1

    async def test_create_sale_card(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
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
                    "payment_method": "card",
                    "amount": 116.00,
                    "currency": "MXN",
                    "bank": "Test Bank",
                    "authorization_code": "AUTH123",
                    "last_four_digits": "1234",
                    "card_type": "visa",
                }],
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    async def test_create_sale_insufficient_stock(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "location_id": str(SEED_LOCATION_ID),
                    "quantity": 9999,
                    "unit_price": 100.00,
                    "tax_rate": 16.00,
                }],
                "payments": [{
                    "payment_method": "cash",
                    "amount": 1160000.00,
                    "currency": "MXN",
                }],
            },
        )
        assert response.status_code == 409
        assert "insuficiente" in response.json()["detail"].lower()

    async def test_create_sale_wrong_payment_total(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
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
                    "amount": 10.00,
                    "currency": "MXN",
                }],
            },
        )
        assert response.status_code == 400
        assert "no coincide" in response.json()["detail"].lower()

    async def test_create_sale_with_discount(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "location_id": str(SEED_LOCATION_ID),
                    "quantity": 1,
                    "unit_price": 100.00,
                    "discount": 10.00,
                    "tax_rate": 16.00,
                }],
                "payments": [{
                    "payment_method": "cash",
                    "amount": 104.40,
                    "currency": "MXN",
                }],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["discount_total"] == 10.00

    async def test_get_sale(self, client: AsyncClient, auth_headers):
        sale = await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
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
            },
        )
        sale_id = sale.json()["id"]

        response = await client.get(f"/api/v1/sales/{sale_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sale_id
        assert "items" in data
        assert "payments" in data

    async def test_search_sales(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
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
            },
        )

        response = await client.get(
            "/api/v1/sales/search",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_cancel_sale(self, client: AsyncClient, auth_headers):
        sale = await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
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
            },
        )
        sale_id = sale.json()["id"]

        response = await client.post(
            f"/api/v1/sales/{sale_id}/cancel",
            headers=auth_headers,
            json={"reason": "Test cancellation"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

        # Verify stock was restored
        inv = await client.get("/api/v1/inventory", headers=auth_headers)
        item = next(i for i in inv.json() if i["product_id"] == str(SEED_PRODUCT_ID))
        assert item["quantity"] == 100

    async def test_cancel_already_cancelled(self, client: AsyncClient, auth_headers):
        sale = await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
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
            },
        )
        sale_id = sale.json()["id"]
        await client.post(
            f"/api/v1/sales/{sale_id}/cancel",
            headers=auth_headers,
            json={"reason": "First cancel"},
        )
        response = await client.post(
            f"/api/v1/sales/{sale_id}/cancel",
            headers=auth_headers,
            json={"reason": "Second cancel"},
        )
        assert response.status_code == 400
        assert "cancelada" in response.json()["detail"].lower()

    async def test_sale_deducts_inventory(self, client: AsyncClient, auth_headers):
        inv_before = await client.get("/api/v1/inventory", headers=auth_headers)
        qty_before = next(
            i["quantity"] for i in inv_before.json()
            if i["product_id"] == str(SEED_PRODUCT_ID)
        )

        await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "location_id": str(SEED_LOCATION_ID),
                    "quantity": 5,
                    "unit_price": 100.00,
                    "tax_rate": 16.00,
                }],
                "payments": [{
                    "payment_method": "cash",
                    "amount": 580.00,
                    "currency": "MXN",
                }],
            },
        )

        inv_after = await client.get("/api/v1/inventory", headers=auth_headers)
        qty_after = next(
            i["quantity"] for i in inv_after.json()
            if i["product_id"] == str(SEED_PRODUCT_ID)
        )
        assert qty_after == qty_before - 5

    async def test_create_sale_no_items(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [],
                "payments": [{
                    "payment_method": "cash",
                    "amount": 0,
                    "currency": "MXN",
                }],
            },
        )
        assert response.status_code == 422

    async def test_create_sale_no_payments(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/sales",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "location_id": str(SEED_LOCATION_ID),
                    "quantity": 1,
                    "unit_price": 100.00,
                    "tax_rate": 16.00,
                }],
                "payments": [],
            },
        )
        assert response.status_code == 422
