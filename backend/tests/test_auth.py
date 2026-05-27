import pytest
from httpx import AsyncClient


class TestAuth:
    async def test_login_success(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "pin": "1234",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "admin"
        assert data["full_name"] == "Admin Test"

    async def test_login_invalid_pin(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "pin": "9999",
        })
        assert response.status_code == 401
        assert "inválidas" in response.json()["detail"].lower()

    async def test_login_invalid_username(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "username": "nonexistent",
            "pin": "1234",
        })
        assert response.status_code == 401

    async def test_login_invalid_pin_format(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "pin": "abc",
        })
        assert response.status_code == 401

    async def test_login_short_pin(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "pin": "12",
        })
        assert response.status_code == 422

    async def test_get_me(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert "permissions" in data

    async def test_get_me_no_token(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid-token-here",
        })
        assert response.status_code == 401

    async def test_logout(self, client: AsyncClient, auth_headers):
        response = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200

    async def test_logout_no_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    async def test_login_lockout(self, client: AsyncClient):
        for _ in range(6):
            response = await client.post("/api/v1/auth/login", json={
                "username": "admin",
                "pin": "9999",
            })
        assert response.status_code == 403
        assert "bloqueado" in response.json()["detail"].lower()

    async def test_protected_endpoint_no_permission(self, client: AsyncClient):
        response = await client.post("/api/v1/products", headers={
            "Authorization": "Bearer invalid",
        }, json={
            "name": "Test",
            "price": 100,
            "cost": 50,
        })
        assert response.status_code in (401, 403)

    async def test_pin_validation_format(self):
        from app.core.security import validate_pin_format
        assert validate_pin_format("1234") is True
        assert validate_pin_format("123456") is True
        assert validate_pin_format("123") is False
        assert validate_pin_format("123456789") is False
        assert validate_pin_format("abcd") is False
        assert validate_pin_format("") is False
        assert validate_pin_format(None) is False
