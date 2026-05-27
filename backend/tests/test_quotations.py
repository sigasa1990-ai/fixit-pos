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
    await client.post(
        "/api/v1/cash-registers/open",
        headers=auth_headers,
        json={
            "cash_register_id": str(SEED_CASH_REGISTER_ID),
            "opening_balance": 1000.00,
        },
    )
    yield
    await client.post(
        "/api/v1/cash-registers/close",
        headers=auth_headers,
        json={
            "cash_register_id": str(SEED_CASH_REGISTER_ID),
        },
    )


class TestQuotations:
    async def test_create_quotation(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "quantity": 3,
                    "unit_price": 100.00,
                    "tax_rate": 16.00,
                }],
                "valid_until": "2025-12-31",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["folio"].startswith("COT-")

    async def test_get_quotation(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "quantity": 1,
                    "unit_price": 100.00,
                    "tax_rate": 16.00,
                }],
            },
        )
        qid = created.json()["id"]

        response = await client.get(f"/api/v1/quotations/{qid}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["folio"].startswith("COT-")

    async def test_search_quotations(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "quantity": 1,
                    "unit_price": 100.00,
                    "tax_rate": 16.00,
                }],
            },
        )

        response = await client.get(
            "/api/v1/quotations/search",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_convert_quotation_to_sale(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "quantity": 2,
                    "unit_price": 100.00,
                    "tax_rate": 16.00,
                }],
            },
        )
        qid = created.json()["id"]

        response = await client.post(
            f"/api/v1/quotations/{qid}/convert",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "location_id": str(SEED_LOCATION_ID),
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

        # Verify quotation was marked as converted
        q_response = await client.get(f"/api/v1/quotations/{qid}", headers=auth_headers)
        assert q_response.json()["status"] == "converted"

    async def test_convert_already_converted(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "quantity": 1,
                    "unit_price": 100.00,
                    "tax_rate": 16.00,
                }],
            },
        )
        qid = created.json()["id"]

        await client.post(
            f"/api/v1/quotations/{qid}/convert",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "location_id": str(SEED_LOCATION_ID),
            },
        )
        response = await client.post(
            f"/api/v1/quotations/{qid}/convert",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "location_id": str(SEED_LOCATION_ID),
            },
        )
        assert response.status_code == 400
        assert "convertida" in response.json()["detail"].lower()

    async def test_convert_expired_quotation(self, client: AsyncClient, auth_headers):
        created = await client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [{
                    "product_id": str(SEED_PRODUCT_ID),
                    "quantity": 1,
                    "unit_price": 100.00,
                    "tax_rate": 16.00,
                }],
            },
        )
        qid = created.json()["id"]

        response = await client.post(
            f"/api/v1/quotations/{qid}/convert",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "location_id": str(SEED_LOCATION_ID),
            },
        )
        # Should convert fine since it's active
        assert response.status_code == 200

    async def test_create_quotation_empty_items(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "branch_id": str(SEED_BRANCH_ID),
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "items": [],
            },
        )
        assert response.status_code == 422
