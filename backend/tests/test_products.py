import pytest
from httpx import AsyncClient
from uuid import UUID


class TestProducts:
    async def test_create_product(self, client: AsyncClient, auth_headers):
        response = await client.post("/api/v1/products", headers=auth_headers, json={
            "name": "Nuevo Producto",
            "price": 150.00,
            "cost": 75.00,
            "tax_rate": 16.00,
            "barcode": "7501234567890",
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["product_code"] == "PRD-000002"

    async def test_create_product_duplicate_barcode(self, client: AsyncClient, auth_headers):
        await client.post("/api/v1/products", headers=auth_headers, json={
            "name": "Producto 1",
            "price": 100,
            "cost": 50,
            "barcode": "6660000000000",
        })
        response = await client.post("/api/v1/products", headers=auth_headers, json={
            "name": "Producto 2",
            "price": 100,
            "cost": 50,
            "barcode": "6660000000000",
        })
        assert response.status_code == 409

    async def test_search_products(self, client: AsyncClient, auth_headers):
        response = await client.get(
            "/api/v1/products/search",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    async def test_search_products_by_name(self, client: AsyncClient, auth_headers):
        response = await client.get(
            "/api/v1/products/search?query=Prueba",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 1
        assert "Prueba" in data["items"][0]["name"]

    async def test_get_product(self, client: AsyncClient, auth_headers):
        search = await client.get("/api/v1/products/search", headers=auth_headers)
        pid = search.json()["items"][0]["id"]

        response = await client.get(f"/api/v1/products/{pid}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == pid

    async def test_get_product_not_found(self, client: AsyncClient, auth_headers):
        response = await client.get(
            "/api/v1/products/00000000-0000-0000-0000-000000099999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_update_product(self, client: AsyncClient, auth_headers):
        search = await client.get("/api/v1/products/search", headers=auth_headers)
        pid = search.json()["items"][0]["id"]

        response = await client.patch(f"/api/v1/products/{pid}", headers=auth_headers, json={
            "name": "Producto Actualizado",
            "price": 200.00,
        })
        assert response.status_code == 200
        assert response.json()["name"] == "Producto Actualizado"
        assert response.json()["price"] == 200.00

    async def test_product_auto_code_generation(self, client: AsyncClient, auth_headers):
        response = await client.post("/api/v1/products", headers=auth_headers, json={
            "name": "Sin Codigo",
            "price": 10,
            "cost": 5,
        })
        assert response.status_code == 200
        assert response.json()["product_code"].startswith("PRD-")
