"""FIXIT POS — Load Tests with Locust

Usage:
    locust -f load-tests/locustfile.py --host=http://localhost:8000
"""
import random
import uuid
from locust import HttpUser, task, between, constant


class POSUser(HttpUser):
    """Simulates a POS cashier performing typical operations."""

    wait_time = between(2, 5)
    token = None
    tenant_id = None
    headers = {}

    def on_start(self):
        """Login as cashier."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "pin": "1234"},
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            self.tenant_id = response.json()["tenant_id"]

    @task(3)
    def search_products(self):
        """Search products by name query."""
        queries = ["producto", "prueba", "test", "laptop", "mouse", "teclado"]
        self.client.get(
            "/api/v1/products/search",
            headers=self.headers,
            params={"query": random.choice(queries), "page_size": 20},
        )

    @task(1)
    def open_close_cash_register(self):
        """Open and close a cash register."""
        # First, list cash registers to find one
        regs = self.client.get(
            "/api/v1/cash-registers",
            headers=self.headers,
        )
        if regs.status_code != 200 or not regs.json():
            return
        reg_id = regs.json()[0]["id"]

        # Try to close first (in case it's open)
        self.client.post(
            "/api/v1/cash-registers/close",
            headers=self.headers,
            json={"cash_register_id": reg_id},
        )

        # Open
        resp = self.client.post(
            "/api/v1/cash-registers/open",
            headers=self.headers,
            json={"cash_register_id": reg_id, "opening_balance": 5000.00},
        )
        if resp.status_code == 200:
            self.open_register_id = reg_id

    @task(5)
    def create_sale(self):
        """Create a sale with a single product."""
        if not hasattr(self, "open_register_id"):
            return

        # Get a product to sell
        products = self.client.get(
            "/api/v1/products/search",
            headers=self.headers,
            params={"page_size": 5},
        )
        if products.status_code != 200 or not products.json().get("items"):
            return
        product = random.choice(products.json()["items"])

        self.client.post(
            "/api/v1/sales",
            headers=self.headers,
            json={
                "branch_id": "00000000-0000-0000-0000-000000000010",
                "cash_register_id": self.open_register_id,
                "items": [{
                    "product_id": product["id"],
                    "location_id": "00000000-0000-0000-0000-000000000020",
                    "quantity": 1,
                    "unit_price": float(product["price"]),
                    "tax_rate": float(product["tax_rate"]),
                }],
                "payments": [{
                    "payment_method": "cash",
                    "amount": float(product["price"]) * 1.16,
                    "currency": "MXN",
                }],
            },
        )

    @task(2)
    def get_inventory(self):
        """Check inventory levels."""
        self.client.get("/api/v1/inventory", headers=self.headers)

    @task(1)
    def validate_stock(self):
        """Validate stock for a product."""
        products = self.client.get(
            "/api/v1/products/search",
            headers=self.headers,
            params={"page_size": 1},
        )
        if products.status_code != 200 or not products.json().get("items"):
            return
        product = products.json()["items"][0]

        self.client.post(
            "/api/v1/inventory/validate-stock",
            headers=self.headers,
            json={
                "items": [{
                    "product_id": product["id"],
                    "location_id": "00000000-0000-0000-0000-000000000020",
                    "quantity": 1,
                }],
            },
        )


class ScannerUser(HttpUser):
    """Simulates continuous barcode scanner input."""

    wait_time = constant(0.5)
    token = None
    headers = {}

    def on_start(self):
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "pin": "1234"},
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(10)
    def scan_barcode(self):
        """Simulate barcode scan product lookup."""
        barcode = f"750{random.randint(1000000000, 9999999999)}"
        self.client.get(
            "/api/v1/products/search",
            headers=self.headers,
            params={"query": barcode, "page_size": 1},
        )


class MultiTenantUser(HttpUser):
    """Simulates operations from different tenants."""

    wait_time = between(1, 3)

    def on_start(self):
        # Use admin credentials from seed data
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "pin": "1234"},
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def tenant_dashboard(self):
        """Check tenant-specific dashboard."""
        self.client.get(
            "/api/v1/dashboard/summary",
            headers=self.headers,
        )

    @task(2)
    def tenant_info(self):
        """Get tenant configuration."""
        self.client.get(
            "/api/v1/tenant/info",
            headers=self.headers,
        )
