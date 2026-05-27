import pytest
from httpx import AsyncClient

from tests.conftest import SEED_CASH_REGISTER_ID


class TestCashRegister:
    async def test_list_cash_registers(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/cash-registers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_get_cash_register(self, client: AsyncClient, auth_headers):
        response = await client.get(
            f"/api/v1/cash-registers/{SEED_CASH_REGISTER_ID}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(SEED_CASH_REGISTER_ID)

    async def test_get_cash_register_not_found(self, client: AsyncClient, auth_headers):
        response = await client.get(
            "/api/v1/cash-registers/00000000-0000-0000-0000-000000099999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_open_cash_register(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/cash-registers/open",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "opening_balance": 500.00,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "open"
        assert data["balance"] == 500.00
        assert "session_id" in data

    async def test_open_already_open(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/cash-registers/open",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "opening_balance": 500.00,
            },
        )
        response = await client.post(
            "/api/v1/cash-registers/open",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "opening_balance": 500.00,
            },
        )
        assert response.status_code == 400
        assert "abierta" in response.json()["detail"].lower()

    async def test_cash_movement(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/cash-registers/open",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "opening_balance": 1000.00,
            },
        )
        response = await client.post(
            "/api/v1/cash-registers/movements",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "amount": 200.00,
                "movement_type": "in",
                "description": "Test deposit",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["balance_after"] == 1200.00

    async def test_cash_movement_closed_register(self, client: AsyncClient, auth_headers):
        # Register is closed by default
        response = await client.post(
            "/api/v1/cash-registers/movements",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "amount": 100.00,
                "movement_type": "in",
                "description": "Test",
            },
        )
        assert response.status_code == 409 or response.status_code == 400

    async def test_close_cash_register(self, client: AsyncClient, auth_headers):
        await client.post(
            "/api/v1/cash-registers/open",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
                "opening_balance": 500.00,
            },
        )
        response = await client.post(
            "/api/v1/cash-registers/close",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"

    async def test_close_closed_register(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/cash-registers/close",
            headers=auth_headers,
            json={
                "cash_register_id": str(SEED_CASH_REGISTER_ID),
            },
        )
        assert response.status_code == 400
        assert "no está abierta" in response.json()["detail"].lower()
