-- ============================================================================
-- FIXIT POS — PostgreSQL Schema Completo
-- Versión: 1.0.0
-- Descripción: Schema multi-tenant para sistema POS SaaS
-- Principios:
--   - tenant_id en TODAS las tablas de negocio
--   - Row-Level Security (RLS) activo en todas las tablas
--   - Constraints CHECK para integridad de datos
--   - Índices compuestos para queries multi-tenant
--   - Triggers de auditoría automática
--   - Transacciones atómicas desde el schema
-- ============================================================================

-- ============================================================================
-- EXTENSIONES
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "citext";         -- case-insensitive text

-- ============================================================================
-- ENUMS
-- ============================================================================
CREATE TYPE user_role_type AS ENUM ('admin', 'supervisor', 'cashier');
CREATE TYPE document_status AS ENUM ('draft', 'active', 'parked', 'converted', 'cancelled', 'completed');
CREATE TYPE cash_register_status AS ENUM ('open', 'closed');
CREATE TYPE movement_type AS ENUM ('sale', 'purchase', 'transfer', 'adjustment', 'return', 'initial');
CREATE TYPE payment_method AS ENUM ('cash', 'card', 'transfer', 'usd', 'mixed');
CREATE TYPE payment_currency AS ENUM ('MXN', 'USD');
CREATE TYPE warranty_type AS ENUM ('standard', 'extended', 'none');
CREATE TYPE audit_action AS ENUM (
    'login', 'logout', 'sale.create', 'sale.cancel', 'sale.refund',
    'cashier.open', 'cashier.close', 'cashier.in', 'cashier.out',
    'inventory.adjust', 'inventory.transfer',
    'product.create', 'product.update', 'product.delete',
    'price.change', 'customer.create', 'customer.update',
    'user.create', 'user.update', 'user.delete',
    'config.update', 'override.pin'
);

-- ============================================================================
-- TABLAS BASE (SIN tenant_id — infraestructura)
-- ============================================================================

-- 1. TENANTS
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name VARCHAR(255) NOT NULL,
    commercial_name VARCHAR(255) NOT NULL,
    rfc VARCHAR(13),
    tax_regime VARCHAR(50),
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    logo_url TEXT,
    website VARCHAR(255),
    social_media JSONB DEFAULT '{}',
    ticket_header TEXT,
    ticket_footer TEXT,
    ticket_policies TEXT,
    primary_color VARCHAR(7) DEFAULT '#2563eb',
    secondary_color VARCHAR(7) DEFAULT '#1e40af',
    pin_timeout_minutes INTEGER DEFAULT 10,
    max_open_orders INTEGER DEFAULT 5,
    currency_symbol VARCHAR(5) DEFAULT '$',
    decimal_places INTEGER DEFAULT 2,
    timezone VARCHAR(50) DEFAULT 'America/Mexico_City',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. PERMISSIONS (catálogo global, sin tenant_id)
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    module VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- TABLAS POR TENANT
-- ============================================================================

-- 3. ROLES (por tenant)
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    role_type user_role_type NOT NULL DEFAULT 'cashier',
    description TEXT,
    is_system BOOLEAN DEFAULT false,  -- roles semilla no eliminables
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

-- 4. ROLE PERMISSIONS
CREATE TABLE role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(role_id, permission_id)
);

-- 5. USERS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id),
    username VARCHAR(50) NOT NULL,
    pin_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    requires_pin_change BOOLEAN DEFAULT false,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    last_login_ip INET,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, username)
);

-- 6. BRANCHES (Sucursales)
CREATE TABLE branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, code)
);

-- 7. USER BRANCH ASSIGNMENT (usuarios pueden operar en múltiples sucursales)
CREATE TABLE user_branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, branch_id)
);

-- 8. WAREHOUSES (Almacenes)
CREATE TABLE warehouses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) DEFAULT 'warehouse',  -- warehouse, showroom, transit
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, code)
);

-- 9. LOCATIONS (Ubicaciones — el nivel más granular de inventario)
CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    barcode VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, warehouse_id, code)
);

-- 10. PRODUCT CATEGORIES
CREATE TABLE product_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES product_categories(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);

-- 11. PRODUCTS
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    category_id UUID REFERENCES product_categories(id),
    product_code VARCHAR(50) NOT NULL,
    barcode VARCHAR(100),
    sku VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(12, 2) NOT NULL CHECK (price >= 0),
    cost DECIMAL(12, 2) NOT NULL CHECK (cost >= 0),
    min_price DECIMAL(12, 2) CHECK (min_price >= 0),
    tax_rate DECIMAL(5, 2) DEFAULT 0.00,
    unit VARCHAR(50) DEFAULT 'pza',
    warranty_days INTEGER DEFAULT 0,
    warranty_type warranty_type DEFAULT 'none',
    is_active BOOLEAN DEFAULT true,
    is_service BOOLEAN DEFAULT false,  -- servicios no tienen inventario
    track_inventory BOOLEAN DEFAULT true,
    image_url TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, product_code),
    UNIQUE(tenant_id, barcode),
    UNIQUE(tenant_id, sku)
);

-- 12. INVENTORY (stock por ubicación)
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    quantity DECIMAL(12, 4) NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    min_stock DECIMAL(12, 4) DEFAULT 0 CHECK (min_stock >= 0),
    max_stock DECIMAL(12, 4) CHECK (max_stock IS NULL OR max_stock >= min_stock),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, product_id, location_id)
);

-- 13. INVENTORY MOVEMENTS (auditoría de inventario)
CREATE TABLE inventory_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    warehouse_id UUID NOT NULL REFERENCES warehouses(id),
    location_id UUID NOT NULL REFERENCES locations(id),
    branch_id UUID NOT NULL REFERENCES branches(id),
    user_id UUID NOT NULL REFERENCES users(id),
    movement_type movement_type NOT NULL,
    reference_type VARCHAR(50),      -- 'sale', 'purchase', 'transfer', etc.
    reference_id UUID,               -- ID de la venta, compra, etc.
    quantity_before DECIMAL(12, 4) NOT NULL,
    quantity_change DECIMAL(12, 4) NOT NULL,
    quantity_after DECIMAL(12, 4) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14. CUSTOMERS
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    rfc VARCHAR(13),
    business_name VARCHAR(255),
    tax_regime VARCHAR(50),
    cfdi_usage VARCHAR(10) DEFAULT 'G01',
    tax_address TEXT,
    is_active BOOLEAN DEFAULT true,
    credit_limit DECIMAL(12, 2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 15. CASH REGISTERS (Cajas)
CREATE TABLE cash_registers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES locations(id),
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status cash_register_status DEFAULT 'closed',
    current_balance DECIMAL(12, 2) DEFAULT 0 CHECK (current_balance >= 0),
    opening_balance DECIMAL(12, 2) DEFAULT 0 CHECK (opening_balance >= 0),
    closed_at TIMESTAMPTZ,
    opened_by UUID REFERENCES users(id),
    closed_by UUID REFERENCES users(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, branch_id, code)
);

-- 16. CASH REGISTER SESSIONS (historial de apertura/cierre)
CREATE TABLE cash_register_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cash_register_id UUID NOT NULL REFERENCES cash_registers(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id),
    opened_by UUID NOT NULL REFERENCES users(id),
    closed_by UUID REFERENCES users(id),
    opening_balance DECIMAL(12, 2) NOT NULL CHECK (opening_balance >= 0),
    closing_balance DECIMAL(12, 2) CHECK (closing_balance >= 0),
    expected_balance DECIMAL(12, 2),
    difference DECIMAL(12, 2),
    total_cash_sales DECIMAL(12, 2) DEFAULT 0,
    total_card_sales DECIMAL(12, 2) DEFAULT 0,
    total_transfer_sales DECIMAL(12, 2) DEFAULT 0,
    total_usd_sales DECIMAL(12, 2) DEFAULT 0,
    total_cash_in DECIMAL(12, 2) DEFAULT 0,
    total_cash_out DECIMAL(12, 2) DEFAULT 0,
    total_sales_count INTEGER DEFAULT 0,
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    notes TEXT,
    UNIQUE(tenant_id, cash_register_id, opened_at)
);

-- 17. CASH REGISTER MOVEMENTS (entradas/salidas de efectivo)
CREATE TABLE cash_register_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cash_register_id UUID NOT NULL REFERENCES cash_registers(id),
    cash_register_session_id UUID NOT NULL REFERENCES cash_register_sessions(id),
    branch_id UUID NOT NULL REFERENCES branches(id),
    user_id UUID NOT NULL REFERENCES users(id),
    movement_type VARCHAR(20) NOT NULL CHECK (movement_type IN ('in', 'out', 'sale', 'expense')),
    amount DECIMAL(12, 2) NOT NULL CHECK (amount > 0),
    balance_before DECIMAL(12, 2) NOT NULL,
    balance_after DECIMAL(12, 2) NOT NULL,
    reference_type VARCHAR(50),   -- 'sale', 'expense', 'withdrawal', 'top_up'
    reference_id UUID,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 18. FOLLO CONTROLS (control de folios atómico)
CREATE TABLE folio_controls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    cash_register_id UUID NOT NULL REFERENCES cash_registers(id) ON DELETE CASCADE,
    document_type VARCHAR(10) NOT NULL,  -- VTA, COT, DEV, CORTE
    prefix VARCHAR(10) NOT NULL,         -- VTA-, COT-, DEV-, CORTE-
    current_number INTEGER NOT NULL DEFAULT 0,
    next_number INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, branch_id, cash_register_id, document_type)
);

-- 19. SALES
CREATE TABLE sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id),
    cash_register_id UUID NOT NULL REFERENCES cash_registers(id),
    cash_register_session_id UUID NOT NULL REFERENCES cash_register_sessions(id),
    user_id UUID NOT NULL REFERENCES users(id),
    customer_id UUID REFERENCES customers(id),
    folio VARCHAR(30) NOT NULL,
    status document_status NOT NULL DEFAULT 'completed',
    subtotal DECIMAL(12, 2) NOT NULL CHECK (subtotal >= 0),
    tax_total DECIMAL(12, 2) NOT NULL DEFAULT 0 CHECK (tax_total >= 0),
    discount_total DECIMAL(12, 2) NOT NULL DEFAULT 0 CHECK (discount_total >= 0),
    total DECIMAL(12, 2) NOT NULL CHECK (total >= 0),
    payment_status VARCHAR(20) DEFAULT 'paid' CHECK (payment_status IN ('pending', 'paid', 'refunded', 'partially_refunded')),
    notes TEXT,
    cancelled_at TIMESTAMPTZ,
    cancelled_by UUID REFERENCES users(id),
    cancel_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, folio)
);

-- 20. SALE ITEMS
CREATE TABLE sale_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sale_id UUID NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    location_id UUID NOT NULL REFERENCES locations(id),
    quantity DECIMAL(12, 4) NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(12, 2) NOT NULL CHECK (unit_price >= 0),
    cost_price DECIMAL(12, 2) NOT NULL CHECK (cost_price >= 0),
    discount DECIMAL(12, 2) NOT NULL DEFAULT 0 CHECK (discount >= 0),
    tax_rate DECIMAL(5, 2) DEFAULT 0.00,
    tax_amount DECIMAL(12, 2) DEFAULT 0,
    subtotal DECIMAL(12, 2) NOT NULL CHECK (subtotal >= 0),
    total DECIMAL(12, 2) NOT NULL CHECK (total >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 21. PAYMENTS (soporta pago mixto — múltiples métodos por venta)
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sale_id UUID NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
    payment_method payment_method NOT NULL,
    currency payment_currency NOT NULL DEFAULT 'MXN',
    amount DECIMAL(12, 2) NOT NULL CHECK (amount > 0),
    amount_mxn DECIMAL(12, 2) NOT NULL CHECK (amount_mxn > 0),  -- siempre en MXN para cuadre de caja
    exchange_rate DECIMAL(10, 4) DEFAULT 1.0000,
    reference VARCHAR(255),       -- número de autorización, referencia, etc.
    bank VARCHAR(100),            -- banco emisor
    authorization_code VARCHAR(50),
    last_four_digits VARCHAR(4),
    card_type VARCHAR(20),        -- crédito, débito
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 22. QUOTATIONS (Cotizaciones)
CREATE TABLE quotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id),
    cash_register_id UUID NOT NULL REFERENCES cash_registers(id),
    user_id UUID NOT NULL REFERENCES users(id),
    customer_id UUID REFERENCES customers(id),
    folio VARCHAR(30) NOT NULL,
    status document_status NOT NULL DEFAULT 'draft',
    subtotal DECIMAL(12, 2) NOT NULL CHECK (subtotal >= 0),
    tax_total DECIMAL(12, 2) DEFAULT 0 CHECK (tax_total >= 0),
    discount_total DECIMAL(12, 2) DEFAULT 0 CHECK (discount_total >= 0),
    total DECIMAL(12, 2) NOT NULL CHECK (total >= 0),
    valid_until DATE,
    notes TEXT,
    converted_to_sale_id UUID REFERENCES sales(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, folio)
);

-- 23. QUOTATION ITEMS
CREATE TABLE quotation_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    quotation_id UUID NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    quantity DECIMAL(12, 4) NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(12, 2) NOT NULL CHECK (unit_price >= 0),
    discount DECIMAL(12, 2) NOT NULL DEFAULT 0 CHECK (discount >= 0),
    tax_rate DECIMAL(5, 2) DEFAULT 0.00,
    tax_amount DECIMAL(12, 2) DEFAULT 0,
    subtotal DECIMAL(12, 2) NOT NULL CHECK (subtotal >= 0),
    total DECIMAL(12, 2) NOT NULL CHECK (total >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 24. WARRANTIES (Garantías)
CREATE TABLE warranties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    sale_id UUID NOT NULL REFERENCES sales(id),
    sale_item_id UUID NOT NULL REFERENCES sale_items(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    product_id UUID NOT NULL REFERENCES products(id),
    user_id UUID NOT NULL REFERENCES users(id),
    warranty_type warranty_type NOT NULL DEFAULT 'standard',
    warranty_days INTEGER NOT NULL DEFAULT 0,
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_warranty_dates CHECK (end_date > start_date)
);

-- 25. AUDIT LOGS
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    branch_id UUID REFERENCES branches(id),
    action audit_action NOT NULL,
    entity_type VARCHAR(50),       -- 'sale', 'product', 'user', etc.
    entity_id UUID,                 -- ID del registro afectado
    description TEXT,
    old_values JSONB,               -- valores anteriores (para cambios)
    new_values JSONB,               -- valores nuevos
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 26. USER SESSIONS (sesiones activas)
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) NOT NULL UNIQUE,  -- JWT ID
    ip_address INET,
    user_agent TEXT,
    logged_in_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    logged_out_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true
);

-- 27. TENANT SETTINGS (configuración dinámica por tenant)
CREATE TABLE tenant_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, setting_key)
);

-- ============================================================================
-- ÍNDICES
-- ============================================================================

-- Multi-tenant: índices compuestos con tenant_id primero
CREATE INDEX idx_roles_tenant ON roles(tenant_id);
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_branches_tenant ON branches(tenant_id);
CREATE INDEX idx_user_branches_tenant ON user_branches(tenant_id);
CREATE INDEX idx_warehouses_tenant ON warehouses(tenant_id);
CREATE INDEX idx_locations_tenant ON locations(tenant_id);
CREATE INDEX idx_categories_tenant ON product_categories(tenant_id);
CREATE INDEX idx_products_tenant ON products(tenant_id);
CREATE INDEX idx_inventory_tenant ON inventory(tenant_id);
CREATE INDEX idx_inventory_movements_tenant ON inventory_movements(tenant_id);
CREATE INDEX idx_customers_tenant ON customers(tenant_id);
CREATE INDEX idx_cash_registers_tenant ON cash_registers(tenant_id);
CREATE INDEX idx_cash_register_sessions_tenant ON cash_register_sessions(tenant_id);
CREATE INDEX idx_cash_register_movements_tenant ON cash_register_movements(tenant_id);
CREATE INDEX idx_folio_controls_tenant ON folio_controls(tenant_id);
CREATE INDEX idx_sales_tenant ON sales(tenant_id);
CREATE INDEX idx_sale_items_tenant ON sale_items(tenant_id);
CREATE INDEX idx_payments_tenant ON payments(tenant_id);
CREATE INDEX idx_quotations_tenant ON quotations(tenant_id);
CREATE INDEX idx_warranties_tenant ON warranties(tenant_id);
CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_sessions_tenant ON user_sessions(tenant_id);

-- Búsqueda rápida en POS (escáner, teclado)
CREATE INDEX idx_products_barcode ON products(tenant_id, barcode) WHERE barcode IS NOT NULL;
CREATE INDEX idx_products_sku ON products(tenant_id, sku) WHERE sku IS NOT NULL;
CREATE INDEX idx_products_code ON products(tenant_id, product_code);
CREATE INDEX idx_products_name_trgm ON products USING gin (name gin_trgm_ops);
CREATE INDEX idx_customers_phone ON customers(tenant_id, phone);
CREATE INDEX idx_customers_rfc ON customers(tenant_id, rfc);
CREATE INDEX idx_customers_name_trgm ON customers USING gin (name gin_trgm_ops);

-- Folios: búsqueda rápida
CREATE INDEX idx_sales_folio ON sales(tenant_id, folio);
CREATE INDEX idx_quotations_folio ON quotations(tenant_id, folio);

-- Auditoría y filtrado por fecha
CREATE INDEX idx_audit_logs_created ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX idx_sales_created ON sales(tenant_id, created_at DESC);
CREATE INDEX idx_sales_user ON sales(tenant_id, user_id, created_at DESC);
CREATE INDEX idx_cash_register_movements_session ON cash_register_movements(cash_register_session_id);

-- Inventario: búsqueda por producto + ubicación
CREATE INDEX idx_inventory_product_location ON inventory(tenant_id, product_id, location_id);
CREATE INDEX idx_inventory_low_stock ON inventory(tenant_id, branch_id, quantity) WHERE quantity <= min_stock;

-- ============================================================================
-- ROW-LEVEL SECURITY (RLS)
-- ============================================================================

-- Habilita RLS en todas las tablas con tenant_id
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE branches ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_branches ENABLE ROW LEVEL SECURITY;
ALTER TABLE warehouses ENABLE ROW LEVEL SECURITY;
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_registers ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_register_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE cash_register_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE folio_controls ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE sale_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE quotations ENABLE ROW LEVEL SECURITY;
ALTER TABLE quotation_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE warranties ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY;

-- Función para obtener tenant_id del contexto de sesión
-- (establecido por el backend al autenticar)
CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS UUID
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN NULLIF(current_setting('app.tenant_id', true), '')::UUID;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$;

-- Función para obtener user_id del contexto de sesión
CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS UUID
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN NULLIF(current_setting('app.user_id', true), '')::UUID;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$;

-- Función para obtener role del contexto de sesión
CREATE OR REPLACE FUNCTION get_current_role()
RETURNS VARCHAR
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN NULLIF(current_setting('app.role', true), '');
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$;

-- Política genérica RLS: solo ver datos del propio tenant
-- (se aplica a TODAS las tablas con tenant_id)
CREATE OR REPLACE FUNCTION tenant_isolation_policy(table_name TEXT)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN format(
        'CREATE POLICY tenant_isolation ON %I
         FOR ALL
         USING (tenant_id = get_current_tenant_id())
         WITH CHECK (tenant_id = get_current_tenant_id())',
        table_name
    );
END;
$$;

-- Aplicar política RLS a cada tabla
-- Nota: en producción esto se haría con una función dinámica,
-- pero aquí lo hacemos explícito para claridad

-- ROLES
CREATE POLICY tenant_isolation_roles ON roles
    FOR ALL USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- USERS
CREATE POLICY tenant_isolation_users ON users
    FOR ALL USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- BRANCHES
CREATE POLICY tenant_isolation_branches ON branches
    FOR ALL USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- PRODUCTS
CREATE POLICY tenant_isolation_products ON products
    FOR ALL USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- INVENTORY
CREATE POLICY tenant_isolation_inventory ON inventory
    FOR ALL USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- SALES
CREATE POLICY tenant_isolation_sales ON sales
    FOR ALL USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- CUSTOMERS
CREATE POLICY tenant_isolation_customers ON customers
    FOR ALL USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- AUDIT LOGS
CREATE POLICY tenant_isolation_audit ON audit_logs
    FOR ALL USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- (Aplicar mismo patrón a todas las tablas con tenant_id)

-- ============================================================================
-- TRIGGER: actualizar updated_at automáticamente
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_roles_updated_at
    BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_branches_updated_at
    BEFORE UPDATE ON branches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_warehouses_updated_at
    BEFORE UPDATE ON warehouses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_locations_updated_at
    BEFORE UPDATE ON locations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON product_categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_inventory_updated_at
    BEFORE UPDATE ON inventory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_cash_registers_updated_at
    BEFORE UPDATE ON cash_registers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_sales_updated_at
    BEFORE UPDATE ON sales
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_quotations_updated_at
    BEFORE UPDATE ON quotations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_warranties_updated_at
    BEFORE UPDATE ON warranties
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_folio_controls_updated_at
    BEFORE UPDATE ON folio_controls
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_tenant_settings_updated_at
    BEFORE UPDATE ON tenant_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- TRIGGER: auditoría automática para cambios críticos en productos
-- ============================================================================
CREATE OR REPLACE FUNCTION audit_product_price_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.price IS DISTINCT FROM NEW.price OR OLD.cost IS DISTINCT FROM NEW.cost THEN
        INSERT INTO audit_logs (
            tenant_id, user_id, action, entity_type, entity_id,
            old_values, new_values, ip_address
        ) VALUES (
            NEW.tenant_id,
            get_current_user_id(),
            'price.change',
            'product',
            NEW.id,
            jsonb_build_object('price', OLD.price, 'cost', OLD.cost),
            jsonb_build_object('price', NEW.price, 'cost', NEW.cost),
            NULL
        );
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_audit_product_price
    AFTER UPDATE OF price, cost ON products
    FOR EACH ROW
    WHEN (OLD.price IS DISTINCT FROM NEW.price OR OLD.cost IS DISTINCT FROM NEW.cost)
    EXECUTE FUNCTION audit_product_price_changes();

-- ============================================================================
-- FUNCIÓN: generar folio atómico (thread-safe)
-- ============================================================================
CREATE OR REPLACE FUNCTION generate_folio(
    p_tenant_id UUID,
    p_branch_id UUID,
    p_cash_register_id UUID,
    p_document_type VARCHAR
)
RETURNS VARCHAR
LANGUAGE plpgsql
AS $$
DECLARE
    v_prefix VARCHAR;
    v_number INTEGER;
    v_folio VARCHAR;
BEGIN
    UPDATE folio_controls
    SET current_number = next_number,
        next_number = next_number + 1,
        updated_at = NOW()
    WHERE tenant_id = p_tenant_id
      AND branch_id = p_branch_id
      AND cash_register_id = p_cash_register_id
      AND document_type = p_document_type
    RETURNING prefix, current_number INTO v_prefix, v_number;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Folio control not found for tenant=% branch=% register=% type=%',
            p_tenant_id, p_branch_id, p_cash_register_id, p_document_type;
    END IF;

    v_folio := v_prefix || LPAD(v_number::TEXT, 6, '0');
    RETURN v_folio;
END;
$$;

-- ============================================================================
-- FUNCIÓN: validar stock disponible (con LOCK)
-- ============================================================================
CREATE OR REPLACE FUNCTION validate_stock_available(
    p_tenant_id UUID,
    p_product_id UUID,
    p_location_id UUID,
    p_quantity DECIMAL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_quantity DECIMAL;
BEGIN
    SELECT quantity INTO v_quantity
    FROM inventory
    WHERE tenant_id = p_tenant_id
      AND product_id = p_product_id
      AND location_id = p_location_id
    FOR UPDATE;  -- LOCK fila para evitar race conditions

    RETURN COALESCE(v_quantity, 0) >= p_quantity;
END;
$$;

-- ============================================================================
-- VISTA: dashboard de ventas del día (por tenant, por sucursal)
-- ============================================================================
CREATE OR REPLACE VIEW v_daily_sales_summary AS
SELECT
    s.tenant_id,
    s.branch_id,
    b.name AS branch_name,
    s.cash_register_id,
    cr.name AS cash_register_name,
    s.user_id,
    u.full_name AS user_name,
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
GROUP BY s.tenant_id, s.branch_id, b.name, s.cash_register_id, cr.name, s.user_id, u.full_name, DATE(s.created_at);

-- ============================================================================
-- VISTA: inventario bajo mínimo
-- ============================================================================
CREATE OR REPLACE VIEW v_low_stock AS
SELECT
    i.tenant_id,
    i.branch_id,
    b.name AS branch_name,
    i.warehouse_id,
    w.name AS warehouse_name,
    i.location_id,
    l.name AS location_name,
    i.product_id,
    p.name AS product_name,
    p.product_code,
    p.barcode,
    i.quantity,
    i.min_stock,
    (i.min_stock - i.quantity) AS deficit
FROM inventory i
JOIN branches b ON b.id = i.branch_id
JOIN warehouses w ON w.id = i.warehouse_id
JOIN locations l ON l.id = i.location_id
JOIN products p ON p.id = i.product_id
WHERE i.quantity <= i.min_stock
  AND p.is_active = true;

-- ============================================================================
-- SEED DATA: Permisos base del sistema
-- ============================================================================
INSERT INTO permissions (code, name, description, module) VALUES
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
    ('role.update', 'Modificar roles', 'Permite modificar roles y permisos', 'roles');

-- ============================================================================
-- NOTAS DE DISEÑO ADICIONALES
-- ============================================================================

-- NOTA 1: La extensión pg_trgm debe instalarse para que los índices
--         GIN trigram funcionen. Habilitar con:
--         CREATE EXTENSION IF NOT EXISTS pg_trgm;
--
-- NOTA 2: RLS requiere que el backend establezca el tenant_id en cada
--         conexión de base de datos:
--         SET app.tenant_id = 'uuid-del-tenant';
--         SET app.user_id = 'uuid-del-user';
--         SET app.role = 'cashier';
--
-- NOTA 3: Las funciones validate_stock_available() y generate_folio()
--         deben usarse DENTRO de transacciones SQL para garantizar
--         atomicidad en operaciones críticas (ventas, folios).
--
-- NOTA 4: Para evitar la necesidad de pg_trgm, se pueden usar
--         ILIKE con índices B-tree en lugar de búsqueda difusa.
--         pg_trgm es recomendado para rendimiento en búsquedas parciales.
