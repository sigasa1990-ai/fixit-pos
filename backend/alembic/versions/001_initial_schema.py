"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-26 23:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


class _EnumNoCreate(sa.Enum):
    """sa.Enum that never auto-creates the type in the DB."""
    def _set_table(self, table, column):
        pass

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop orphaned enums (in case previous migration failed mid-way)
    for enum_name in [
        "user_role_type", "document_status", "cash_register_status",
        "movement_type", "payment_method", "payment_currency",
        "warranty_type", "audit_action",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name} CASCADE")

    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # Enums (fresh creation)
    op.execute("CREATE TYPE user_role_type AS ENUM ('admin', 'supervisor', 'cashier')")
    op.execute("CREATE TYPE document_status AS ENUM ('draft', 'active', 'parked', 'converted', 'cancelled', 'completed')")
    op.execute("CREATE TYPE cash_register_status AS ENUM ('open', 'closed')")
    op.execute("CREATE TYPE movement_type AS ENUM ('sale', 'purchase', 'transfer', 'adjustment', 'return', 'initial')")
    op.execute("CREATE TYPE payment_method AS ENUM ('cash', 'card', 'transfer', 'usd', 'mixed')")
    op.execute("CREATE TYPE payment_currency AS ENUM ('MXN', 'USD')")
    op.execute("CREATE TYPE warranty_type AS ENUM ('standard', 'extended', 'none')")
    op.execute("""
        CREATE TYPE audit_action AS ENUM (
            'login', 'logout', 'sale.create', 'sale.cancel', 'sale.refund',
            'cashier.open', 'cashier.close', 'cashier.in', 'cashier.out',
            'inventory.adjust', 'inventory.transfer',
            'product.create', 'product.update', 'product.delete',
            'price.change', 'customer.create', 'customer.update',
            'user.create', 'user.update', 'user.delete',
            'config.update', 'override.pin'
        )
    """)

    # 1. Tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("commercial_name", sa.String(255), nullable=False),
        sa.Column("rfc", sa.String(13), nullable=True),
        sa.Column("tax_regime", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("social_media", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=True),
        sa.Column("ticket_header", sa.Text(), nullable=True),
        sa.Column("ticket_footer", sa.Text(), nullable=True),
        sa.Column("ticket_policies", sa.Text(), nullable=True),
        sa.Column("primary_color", sa.String(7), server_default="#2563eb", nullable=True),
        sa.Column("secondary_color", sa.String(7), server_default="#1e40af", nullable=True),
        sa.Column("pin_timeout_minutes", sa.Integer(), server_default="10", nullable=True),
        sa.Column("max_open_orders", sa.Integer(), server_default="5", nullable=True),
        sa.Column("currency_symbol", sa.String(5), server_default="$", nullable=True),
        sa.Column("decimal_places", sa.Integer(), server_default="2", nullable=True),
        sa.Column("timezone", sa.String(50), server_default="America/Mexico_City", nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Permissions
    op.create_table(
        "permissions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("module", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # 3. Roles
    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role_type", _EnumNoCreate("admin", "supervisor", "cashier", name="user_role_type"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name"),
    )

    # 4. Role Permissions
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "permission_id"),
    )

    # 5. Users
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("pin_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("requires_pin_change", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), server_default="0", nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "username"),
    )

    # 6. Branches
    op.create_table(
        "branches",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code"),
    )

    # 7. User Branches
    op.create_table(
        "user_branches",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "branch_id"),
    )

    # 8. Warehouses
    op.create_table(
        "warehouses",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), server_default="warehouse", nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code"),
    )

    # 9. Locations
    op.create_table(
        "locations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("warehouse_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("barcode", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "warehouse_id", "code"),
    )

    # 10. Product Categories
    op.create_table(
        "product_categories",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["product_categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name"),
    )

    # 11. Products
    op.create_table(
        "products",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("category_id", sa.UUID(), nullable=True),
        sa.Column("product_code", sa.String(50), nullable=False),
        sa.Column("barcode", sa.String(100), nullable=True),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("min_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("tax_rate", sa.Numeric(5, 2), server_default="0.00", nullable=True),
        sa.Column("unit", sa.String(50), server_default="pza", nullable=True),
        sa.Column("warranty_days", sa.Integer(), server_default="0", nullable=True),
        sa.Column("warranty_type", _EnumNoCreate("standard", "extended", "none", name="warranty_type"), server_default="none", nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("is_service", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("track_inventory", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("price >= 0"),
        sa.CheckConstraint("cost >= 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["product_categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "product_code"),
        sa.UniqueConstraint("tenant_id", "barcode"),
        sa.UniqueConstraint("tenant_id", "sku"),
    )

    # 12. Inventory
    op.create_table(
        "inventory",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("warehouse_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), server_default="0", nullable=False),
        sa.Column("min_stock", sa.Numeric(12, 4), server_default="0", nullable=True),
        sa.Column("max_stock", sa.Numeric(12, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("quantity >= 0"),
        sa.CheckConstraint("min_stock >= 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "product_id", "location_id"),
    )

    # 13. Inventory Movements
    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("warehouse_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("movement_type", _EnumNoCreate("sale", "purchase", "transfer", "adjustment", "return", "initial", name="movement_type"), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.UUID(), nullable=True),
        sa.Column("quantity_before", sa.Numeric(12, 4), nullable=False),
        sa.Column("quantity_change", sa.Numeric(12, 4), nullable=False),
        sa.Column("quantity_after", sa.Numeric(12, 4), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 14. Customers
    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("rfc", sa.String(13), nullable=True),
        sa.Column("business_name", sa.String(255), nullable=True),
        sa.Column("tax_regime", sa.String(50), nullable=True),
        sa.Column("cfdi_usage", sa.String(10), server_default="G01", nullable=True),
        sa.Column("tax_address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("credit_limit", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 15. Cash Registers
    op.create_table(
        "cash_registers",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", _EnumNoCreate("open", "closed", name="cash_register_status"), server_default="closed", nullable=True),
        sa.Column("current_balance", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("opening_balance", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_by", sa.UUID(), nullable=True),
        sa.Column("closed_by", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("current_balance >= 0"),
        sa.CheckConstraint("opening_balance >= 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opened_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "branch_id", "code"),
    )

    # 16. Cash Register Sessions
    op.create_table(
        "cash_register_sessions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("cash_register_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("opened_by", sa.UUID(), nullable=False),
        sa.Column("closed_by", sa.UUID(), nullable=True),
        sa.Column("opening_balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("closing_balance", sa.Numeric(12, 2), nullable=True),
        sa.Column("expected_balance", sa.Numeric(12, 2), nullable=True),
        sa.Column("difference", sa.Numeric(12, 2), nullable=True),
        sa.Column("total_cash_sales", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("total_card_sales", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("total_transfer_sales", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("total_usd_sales", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("total_cash_in", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("total_cash_out", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("total_sales_count", sa.Integer(), server_default="0", nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("opening_balance >= 0"),
        sa.CheckConstraint("closing_balance >= 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cash_register_id"], ["cash_registers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opened_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "cash_register_id", "opened_at"),
    )

    # 17. Cash Register Movements
    op.create_table(
        "cash_register_movements",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("cash_register_id", sa.UUID(), nullable=False),
        sa.Column("cash_register_session_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("movement_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_before", sa.Numeric(12, 2), nullable=False),
        sa.Column("balance_after", sa.Numeric(12, 2), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", sa.UUID(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("amount > 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cash_register_id"], ["cash_registers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cash_register_session_id"], ["cash_register_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 18. Folio Controls
    op.create_table(
        "folio_controls",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("cash_register_id", sa.UUID(), nullable=False),
        sa.Column("document_type", sa.String(10), nullable=False),
        sa.Column("prefix", sa.String(10), nullable=False),
        sa.Column("current_number", sa.Integer(), server_default="0", nullable=True),
        sa.Column("next_number", sa.Integer(), server_default="1", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cash_register_id"], ["cash_registers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "branch_id", "cash_register_id", "document_type"),
    )

    # 19. Sales
    op.create_table(
        "sales",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("cash_register_id", sa.UUID(), nullable=False),
        sa.Column("cash_register_session_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("folio", sa.String(30), nullable=False),
        sa.Column("status", _EnumNoCreate("draft", "active", "parked", "converted", "cancelled", "completed", name="document_status"), server_default="completed", nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_total", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("discount_total", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_status", sa.String(20), server_default="paid", nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.UUID(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("subtotal >= 0"),
        sa.CheckConstraint("tax_total >= 0"),
        sa.CheckConstraint("discount_total >= 0"),
        sa.CheckConstraint("total >= 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cash_register_id"], ["cash_registers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cash_register_session_id"], ["cash_register_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "folio"),
    )

    # 20. Sale Items
    op.create_table(
        "sale_items",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("sale_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("cost_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), server_default="0.00", nullable=True),
        sa.Column("tax_amount", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("quantity > 0"),
        sa.CheckConstraint("unit_price >= 0"),
        sa.CheckConstraint("cost_price >= 0"),
        sa.CheckConstraint("discount >= 0"),
        sa.CheckConstraint("subtotal >= 0"),
        sa.CheckConstraint("total >= 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 21. Payments
    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("sale_id", sa.UUID(), nullable=False),
        sa.Column("payment_method", _EnumNoCreate("cash", "card", "transfer", "usd", "mixed", name="payment_method"), nullable=False),
        sa.Column("currency", _EnumNoCreate("MXN", "USD", name="payment_currency"), server_default="MXN", nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_mxn", sa.Numeric(12, 2), nullable=False),
        sa.Column("exchange_rate", sa.Numeric(10, 4), server_default="1.0000", nullable=True),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("bank", sa.String(100), nullable=True),
        sa.Column("authorization_code", sa.String(50), nullable=True),
        sa.Column("last_four_digits", sa.String(4), nullable=True),
        sa.Column("card_type", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("amount > 0"),
        sa.CheckConstraint("amount_mxn > 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 22. Quotations
    op.create_table(
        "quotations",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("cash_register_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("folio", sa.String(30), nullable=False),
        sa.Column("status", _EnumNoCreate("draft", "active", "parked", "converted", "cancelled", "completed", name="document_status"), server_default="draft", nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_total", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("discount_total", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("converted_to_sale_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("subtotal >= 0"),
        sa.CheckConstraint("tax_total >= 0"),
        sa.CheckConstraint("discount_total >= 0"),
        sa.CheckConstraint("total >= 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cash_register_id"], ["cash_registers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["converted_to_sale_id"], ["sales.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "folio"),
    )

    # 23. Quotation Items
    op.create_table(
        "quotation_items",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("quotation_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), server_default="0.00", nullable=True),
        sa.Column("tax_amount", sa.Numeric(12, 2), server_default="0", nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("quantity > 0"),
        sa.CheckConstraint("unit_price >= 0"),
        sa.CheckConstraint("discount >= 0"),
        sa.CheckConstraint("subtotal >= 0"),
        sa.CheckConstraint("total >= 0"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 24. Warranties
    op.create_table(
        "warranties",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("sale_id", sa.UUID(), nullable=False),
        sa.Column("sale_item_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("warranty_type", _EnumNoCreate("standard", "extended", "none", name="warranty_type"), server_default="standard", nullable=True),
        sa.Column("warranty_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("start_date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.CheckConstraint("end_date > start_date"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_item_id"], ["sale_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 25. Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=True),
        sa.Column("action", _EnumNoCreate(
            "login", "logout", "sale.create", "sale.cancel", "sale.refund",
            "cashier.open", "cashier.close", "cashier.in", "cashier.out",
            "inventory.adjust", "inventory.transfer",
            "product.create", "product.update", "product.delete",
            "price.change", "customer.create", "customer.update",
            "user.create", "user.update", "user.delete",
            "config.update", "override.pin", name="audit_action",
        ), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("old_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 26. User Sessions
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("token_jti", sa.String(255), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("logged_in_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("logged_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_jti"),
    )

    # 27. Tenant Settings
    op.create_table(
        "tenant_settings",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("setting_key", sa.String(100), nullable=False),
        sa.Column("setting_value", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "setting_key"),
    )

    # === IDEMPOTENCY TABLE (for payment idempotency) ===
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("request_hash", sa.String(64), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "idempotency_key"),
    )

    # === SOFT DELETE COLUMNS added to critical tables ===
    op.add_column("sales", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sales", sa.Column("deleted_by", sa.UUID(), nullable=True))
    op.add_column("payments", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("deleted_by", sa.UUID(), nullable=True))
    op.add_column("customers", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("customers", sa.Column("deleted_by", sa.UUID(), nullable=True))
    op.add_column("products", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("products", sa.Column("deleted_by", sa.UUID(), nullable=True))

    # === INDEXES ===
    indexes = [
        "CREATE INDEX idx_roles_tenant ON roles(tenant_id)",
        "CREATE INDEX idx_users_tenant ON users(tenant_id)",
        "CREATE INDEX idx_branches_tenant ON branches(tenant_id)",
        "CREATE INDEX idx_user_branches_tenant ON user_branches(tenant_id)",
        "CREATE INDEX idx_warehouses_tenant ON warehouses(tenant_id)",
        "CREATE INDEX idx_locations_tenant ON locations(tenant_id)",
        "CREATE INDEX idx_categories_tenant ON product_categories(tenant_id)",
        "CREATE INDEX idx_products_tenant ON products(tenant_id)",
        "CREATE INDEX idx_inventory_tenant ON inventory(tenant_id)",
        "CREATE INDEX idx_inventory_movements_tenant ON inventory_movements(tenant_id)",
        "CREATE INDEX idx_customers_tenant ON customers(tenant_id)",
        "CREATE INDEX idx_cash_registers_tenant ON cash_registers(tenant_id)",
        "CREATE INDEX idx_cash_register_sessions_tenant ON cash_register_sessions(tenant_id)",
        "CREATE INDEX idx_cash_register_movements_tenant ON cash_register_movements(tenant_id)",
        "CREATE INDEX idx_folio_controls_tenant ON folio_controls(tenant_id)",
        "CREATE INDEX idx_sales_tenant ON sales(tenant_id)",
        "CREATE INDEX idx_sale_items_tenant ON sale_items(tenant_id)",
        "CREATE INDEX idx_payments_tenant ON payments(tenant_id)",
        "CREATE INDEX idx_quotations_tenant ON quotations(tenant_id)",
        "CREATE INDEX idx_warranties_tenant ON warranties(tenant_id)",
        "CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id)",
        "CREATE INDEX idx_sessions_tenant ON user_sessions(tenant_id)",
        "CREATE INDEX idx_products_barcode ON products(tenant_id, barcode) WHERE barcode IS NOT NULL",
        "CREATE INDEX idx_products_sku ON products(tenant_id, sku) WHERE sku IS NOT NULL",
        "CREATE INDEX idx_products_code ON products(tenant_id, product_code)",
        "CREATE INDEX idx_customers_phone ON customers(tenant_id, phone)",
        "CREATE INDEX idx_customers_rfc ON customers(tenant_id, rfc)",
        "CREATE INDEX idx_sales_folio ON sales(tenant_id, folio)",
        "CREATE INDEX idx_quotations_folio ON quotations(tenant_id, folio)",
        "CREATE INDEX idx_audit_logs_created ON audit_logs(tenant_id, created_at DESC)",
        "CREATE INDEX idx_sales_created ON sales(tenant_id, created_at DESC)",
        "CREATE INDEX idx_sales_user ON sales(tenant_id, user_id, created_at DESC)",
        "CREATE INDEX idx_cash_register_movements_session ON cash_register_movements(cash_register_session_id)",
        "CREATE INDEX idx_inventory_product_location ON inventory(tenant_id, product_id, location_id)",
        "CREATE INDEX idx_inventory_low_stock ON inventory(tenant_id, branch_id, quantity) WHERE quantity <= min_stock",
    ]
    for idx in indexes:
        op.execute(idx)

    # === RLS ===
    rls_tables = [
        "roles", "role_permissions", "users", "branches", "user_branches",
        "warehouses", "locations", "product_categories", "products",
        "inventory", "inventory_movements", "customers", "cash_registers",
        "cash_register_sessions", "cash_register_movements", "folio_controls",
        "sales", "sale_items", "payments", "quotations", "quotation_items",
        "warranties", "audit_logs", "user_sessions", "tenant_settings",
    ]
    for table in rls_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # === RLS Functions ===
    op.execute("""
        CREATE OR REPLACE FUNCTION get_current_tenant_id()
        RETURNS UUID LANGUAGE plpgsql STABLE AS $$
        BEGIN
            RETURN NULLIF(current_setting('app.tenant_id', true), '')::UUID;
        EXCEPTION WHEN OTHERS THEN RETURN NULL;
        END;
        $$;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION get_current_user_id()
        RETURNS UUID LANGUAGE plpgsql STABLE AS $$
        BEGIN
            RETURN NULLIF(current_setting('app.user_id', true), '')::UUID;
        EXCEPTION WHEN OTHERS THEN RETURN NULL;
        END;
        $$;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION get_current_role()
        RETURNS VARCHAR LANGUAGE plpgsql STABLE AS $$
        BEGIN
            RETURN NULLIF(current_setting('app.role', true), '');
        EXCEPTION WHEN OTHERS THEN RETURN NULL;
        END;
        $$;
    """)

    # === RLS Policies ===
    for table in rls_tables:
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            FOR ALL USING (tenant_id = get_current_tenant_id())
            WITH CHECK (tenant_id = get_current_tenant_id())
        """)

    # === Updated_at trigger function ===
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$;
    """)

    # === Updated_at triggers ===
    trigger_tables = [
        "tenants", "users", "roles", "branches", "warehouses",
        "locations", "product_categories", "products", "inventory",
        "customers", "cash_registers", "sales", "quotations",
        "warranties", "folio_controls", "tenant_settings",
    ]
    for table in trigger_tables:
        op.execute(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
        """)

    # === Price audit trigger ===
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_product_price_changes()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.price IS DISTINCT FROM NEW.price OR OLD.cost IS DISTINCT FROM NEW.cost THEN
                INSERT INTO audit_logs (tenant_id, user_id, action, entity_type, entity_id, old_values, new_values)
                VALUES (NEW.tenant_id, get_current_user_id(), 'price.change', 'product', NEW.id,
                    jsonb_build_object('price', OLD.price, 'cost', OLD.cost),
                    jsonb_build_object('price', NEW.price, 'cost', NEW.cost));
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_audit_product_price
        AFTER UPDATE OF price, cost ON products
        FOR EACH ROW
        WHEN (OLD.price IS DISTINCT FROM NEW.price OR OLD.cost IS DISTINCT FROM NEW.cost)
        EXECUTE FUNCTION audit_product_price_changes()
    """)

    # === Permission seed data ===
    permissions_data = [
        ('sale.create', 'Crear venta', 'Permite registrar una nueva venta', 'sales'),
        ('sale.read', 'Consultar ventas', 'Permite consultar ventas realizadas', 'sales'),
        ('sale.read_global', 'Consultar ventas globales', 'Permite consultar ventas de todos los usuarios', 'sales'),
        ('sale.cancel', 'Cancelar venta', 'Permite cancelar una venta existente', 'sales'),
        ('sale.refund', 'Realizar devolución', 'Permite realizar devoluciones', 'sales'),
        ('sale.price_override', 'Sobreescribir precio', 'Permite cambiar precio en venta', 'sales'),
        ('product.create', 'Crear producto', 'Permite crear nuevos productos', 'products'),
        ('product.read', 'Consultar productos', 'Permite consultar el catálogo', 'products'),
        ('product.read_cost', 'Ver costo', 'Permite ver el costo de productos', 'products'),
        ('product.update', 'Actualizar producto', 'Permite modificar productos', 'products'),
        ('product.delete', 'Eliminar producto', 'Permite eliminar productos', 'products'),
        ('inventory.read', 'Consultar inventario', 'Permite consultar niveles de inventario', 'inventory'),
        ('inventory.adjust', 'Ajustar inventario', 'Permite realizar ajustes de inventario', 'inventory'),
        ('inventory.transfer', 'Transferir inventario', 'Permite transferir entre ubicaciones', 'inventory'),
        ('customer.create', 'Crear cliente', 'Permite registrar nuevos clientes', 'customers'),
        ('customer.read', 'Consultar clientes', 'Permite consultar clientes', 'customers'),
        ('customer.update', 'Actualizar cliente', 'Permite modificar datos de clientes', 'customers'),
        ('cashier.open', 'Abrir caja', 'Permite abrir sesión de caja', 'cash_register'),
        ('cashier.close', 'Cerrar caja', 'Permite cerrar sesión de caja', 'cash_register'),
        ('cashier.in', 'Ingreso efectivo', 'Permite registrar entrada de efectivo', 'cash_register'),
        ('cashier.out', 'Salida efectivo', 'Permite registrar salida de efectivo', 'cash_register'),
        ('cashier.read_global', 'Ver movimientos globales', 'Permite ver movimientos de todas las cajas', 'cash_register'),
        ('quotation.create', 'Crear cotización', 'Permite crear cotizaciones', 'quotations'),
        ('quotation.read', 'Consultar cotizaciones', 'Permite consultar cotizaciones', 'quotations'),
        ('quotation.convert', 'Convertir a venta', 'Permite convertir cotización en venta', 'quotations'),
        ('quotation.cancel', 'Cancelar cotización', 'Permite cancelar cotizaciones', 'quotations'),
        ('report.read', 'Ver reportes', 'Permite acceder a reportes y dashboard', 'reports'),
        ('report.read_global', 'Ver reportes globales', 'Permite ver reportes de todo el negocio', 'reports'),
        ('config.read', 'Ver configuración', 'Permite consultar configuración del sistema', 'config'),
        ('config.update', 'Modificar configuración', 'Permite cambiar configuración del sistema', 'config'),
        ('user.create', 'Crear usuario', 'Permite crear usuarios del sistema', 'users'),
        ('user.read', 'Consultar usuarios', 'Permite consultar usuarios', 'users'),
        ('user.update', 'Actualizar usuario', 'Permite modificar usuarios', 'users'),
        ('user.delete', 'Eliminar usuario', 'Permite eliminar usuarios', 'users'),
        ('audit.read', 'Ver auditoría', 'Permite consultar registros de auditoría', 'audit'),
        ('override.pin', 'Override admin', 'Permite autorizar operaciones con PIN de admin', 'security'),
        ('role.read', 'Consultar roles', 'Permite consultar roles', 'roles'),
        ('role.update', 'Modificar roles', 'Permite modificar roles y permisos', 'roles'),
    ]
    for code, name, desc, module in permissions_data:
        op.execute(
            "INSERT INTO permissions (code, name, description, module) VALUES "
            f"('{code}', '{name}', '{desc}', '{module}') "
            "ON CONFLICT (code) DO NOTHING"
        )

    # === Views ===
    op.execute("""
        CREATE OR REPLACE VIEW v_daily_sales_summary AS
        SELECT
            s.tenant_id, s.branch_id, b.name AS branch_name,
            s.cash_register_id, cr.name AS cash_register_name,
            s.user_id, u.full_name AS user_name,
            DATE(s.created_at) AS sale_date,
            COUNT(*) AS total_transactions,
            SUM(s.total) AS total_sales,
            SUM(s.subtotal) AS total_subtotal,
            SUM(s.tax_total) AS total_tax,
            SUM(s.discount_total) AS total_discount,
            COUNT(DISTINCT s.customer_id) AS unique_customers,
            AVG(s.total) AS average_ticket
        FROM sales s
        JOIN branches b ON b.id = s.branch_id
        JOIN cash_registers cr ON cr.id = s.cash_register_id
        JOIN users u ON u.id = s.user_id
        WHERE s.status = 'completed'
        GROUP BY s.tenant_id, s.branch_id, b.name, s.cash_register_id, cr.name, s.user_id, u.full_name, DATE(s.created_at)
    """)
    op.execute("""
        CREATE OR REPLACE VIEW v_low_stock AS
        SELECT
            i.tenant_id, i.branch_id, b.name AS branch_name,
            i.warehouse_id, w.name AS warehouse_name,
            i.location_id, l.name AS location_name,
            i.product_id, p.name AS product_name, p.product_code, p.barcode,
            i.quantity, i.min_stock, (i.min_stock - i.quantity) AS deficit
        FROM inventory i
        JOIN branches b ON b.id = i.branch_id
        JOIN warehouses w ON w.id = i.warehouse_id
        JOIN locations l ON l.id = i.location_id
        JOIN products p ON p.id = i.product_id
        WHERE i.quantity <= i.min_stock AND p.is_active = true
    """)

    # === Folio generation function ===
    op.execute("""
        CREATE OR REPLACE FUNCTION generate_folio(
            p_tenant_id UUID, p_branch_id UUID, p_cash_register_id UUID, p_document_type VARCHAR
        ) RETURNS VARCHAR LANGUAGE plpgsql AS $$
        DECLARE
            v_prefix VARCHAR;
            v_number INTEGER;
        BEGIN
            UPDATE folio_controls
            SET current_number = next_number, next_number = next_number + 1, updated_at = NOW()
            WHERE tenant_id = p_tenant_id AND branch_id = p_branch_id
              AND cash_register_id = p_cash_register_id AND document_type = p_document_type
            RETURNING prefix, current_number INTO v_prefix, v_number;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Folio control not found for tenant=% branch=% register=% type=%',
                    p_tenant_id, p_branch_id, p_cash_register_id, p_document_type;
            END IF;
            RETURN v_prefix || LPAD(v_number::TEXT, 6, '0');
        END;
        $$;
    """)

    # === Stock validation function ===
    op.execute("""
        CREATE OR REPLACE FUNCTION validate_stock_available(
            p_tenant_id UUID, p_product_id UUID, p_location_id UUID, p_quantity DECIMAL
        ) RETURNS BOOLEAN LANGUAGE plpgsql AS $$
        DECLARE v_quantity DECIMAL;
        BEGIN
            SELECT quantity INTO v_quantity FROM inventory
            WHERE tenant_id = p_tenant_id AND product_id = p_product_id AND location_id = p_location_id
            FOR UPDATE;
            RETURN COALESCE(v_quantity, 0) >= p_quantity;
        END;
        $$;
    """)


def downgrade() -> None:
    # Drop views
    op.execute("DROP VIEW IF EXISTS v_low_stock")
    op.execute("DROP VIEW IF EXISTS v_daily_sales_summary")

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS validate_stock_available")
    op.execute("DROP FUNCTION IF EXISTS generate_folio")
    op.execute("DROP FUNCTION IF EXISTS audit_product_price_changes")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column")
    op.execute("DROP FUNCTION IF EXISTS get_current_role")
    op.execute("DROP FUNCTION IF EXISTS get_current_user_id")
    op.execute("DROP FUNCTION IF EXISTS get_current_tenant_id")

    # Drop triggers (already handled by CASCADE on tables)

    # Drop tables in reverse dependency order
    tables = [
        "idempotency_keys",
        "tenant_settings",
        "user_sessions",
        "audit_logs",
        "warranties",
        "quotation_items",
        "quotations",
        "payments",
        "sale_items",
        "sales",
        "folio_controls",
        "cash_register_movements",
        "cash_register_sessions",
        "cash_registers",
        "customers",
        "inventory_movements",
        "inventory",
        "products",
        "product_categories",
        "locations",
        "warehouses",
        "user_branches",
        "branches",
        "users",
        "role_permissions",
        "roles",
        "permissions",
        "tenants",
    ]
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    # Drop enums
    enums = ["audit_action", "warranty_type", "payment_currency", "payment_method",
             "movement_type", "cash_register_status", "document_status", "user_role_type"]
    for enum_name in enums:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
