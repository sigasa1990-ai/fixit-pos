# FIXIT POS — Architecture Design (Stage 1)

## 1. Stack Decisiones

| Capa | Tecnología | Razón |
|------|-----------|-------|
| Frontend | Next.js 14 (App Router) + React 18 | SSR, SEO, server actions, RSC |
| UI | Tailwind CSS + shadcn/ui | Rapidez, componentes accesibles, tema claro/oscuro |
| Backend | FastAPI (Python 3.11+) | Async, type hints nativos, OpenAPI automático, rendimiento |
| ORM | SQLAlchemy 2.0 (async) + Alembic | Migraciones, multi-tenant nativo, transacciones |
| DB | PostgreSQL 16 | JSONB, CTE, ventanas, partitioning, confiabilidad |
| Cache | Redis 7 (opcional Fase 2) | Sesiones, rate limiting, caché productos |
| Auth | JWT + bcrypt (PIN hasheado) | Stateless, rápido, sin sesiones en DB |
| Infrastructure | Docker + Vercel (frontend) + Render (backend) | SaaS simple, escalado horizontal sin ops |
| Storage | Backblaze B2 (S3-compatible) | Logos, plantillas, respaldos |
| Queue | Redis + RQ / Celery (Fase 2) | Tareas async (impresión, facturación) |

---

## 2. Arquitectura General — Modular Monolith

```
┌──────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │ POS      │ │ Caja     │ │ Productos│ │ Dashboard││
│  │ Screen   │ │ Module   │ │ Module   │ │ Module   ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘│
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │Clientes  │ │Reportes  │ │Config    │ │Cotizacion││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘│
└──────────────────┬───────────────────────────────────┘
                   │ HTTP/REST + WebSocket
                   ▼
┌──────────────────────────────────────────────────────┐
│                 Backend (FastAPI)                     │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ API Gateway  │  │ Auth        │  │ Middleware   │  │
│  │ (middleware) │  │ Middleware   │  │ Multi-tenant│  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │ POS      │ │ Inventory ││ Catalog  │ │ Customers ││
│  │ Module   │ │ Module   │ │ Module   │ │ Module   ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘│
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │Cashier   │ │Reports   │ │ Audit    │ │Integratio││
│  │Module    │ │Module    │ │ Module   │ │ Module   ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘│
│                                                      │
│  ┌──────────────────────────────────────────────────┐│
│  │           Shared Core Layer                       ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          ││
│  │  │ Folios   │ │ Tenant   │ │ Payments │          ││
│  │  │ Engine   │ │ Context  │ │ Engine   │          ││
│  │  └──────────┘ └──────────┘ └──────────┘          ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          ││
│  │  │ Permisos │ │  Audit   │ │Webhook   │          ││
│  │  │ Engine   │ │  Engine  │ │ Engine   │          ││
│  │  └──────────┘ └──────────┘ └──────────┘          ││
│  └──────────────────────────────────────────────────┘│
└──────────────────┬───────────────────────────────────┘
                   │ SQLAlchemy async sessions
                   ▼
┌──────────────────────────────────────────────────────┐
│               PostgreSQL (1 DB, schema-per-tenant     │
│               OR row-level tenant_id)                │
└──────────────────────────────────────────────────────┘
```

### Modular Monolith — Reglas

- **Un solo deploy**, múltiples módulos Python (fastapi APIRouter)
- Cada módulo es un `router` + `service` + `repository` + `schema`
- Capa compartida: `core/` (tenant, auth, audit, folios, payments)
- NO microservicios — la comunicación entre módulos es directa (Python calls)
- Escalamiento: múltiples workers del mismo monolith detrás de un load balancer

---

## 3. Multi-Tenant Strategy

### Modelo: **Row-Level tenant_id** (Shared DB, Shared Schema)

```
Ventajas para MVP:
- Un solo PostgreSQL
- Migraciones simples (Alembic)
- Consultas cross-tenant para superadmin (futuro)
- Fácil backup/restore
- Menor overhead operativo
```

### Implementación:

```python
# Cada tabla crítica tiene:
tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)

# Middleware que inyecta tenant_id automáticamente:
# 1. Request llega con JWT → extrae tenant_id del token
# 2. SQLAlchemy query filter automático (see `tenant_filter`):
#    .filter(Model.tenant_id == current_tenant_id)
# 3. Nunca se olvida — es parte del BaseRepository
```

### Tablas con tenant_id:
| Tabla | tenant_id? |
|-------|-----------|
| tenants | NO (es la raíz) |
| users | SÍ |
| roles | SÍ |
| products | SÍ |
| inventory | SÍ |
| sales | SÍ |
| sale_items | SÍ |
| quotations | SÍ |
| customers | SÍ |
| cash_registers | SÍ |
| audit_logs | SÍ |
| warehouses | SÍ |
| locations | SÍ |
| payments | SÍ |
| folio_controls | SÍ |

### Datos por tenant:
```
- Logo (Backblaze B2 URL)
- Nombre comercial
- Colores (primary, secondary)
- RFC
- Régimen fiscal
- Dirección
- Redes sociales
- Políticas (texto para ticket)
- Preferencias (timeout PIN, límite órdenes, etc.)
```

---

## 4. Estrategia de Autenticación

### Login por PIN (Primary)

```
Flujo:
1. Cajero ingresa PIN (4-8 dígitos)
2. Backend busca user por tenant_id + PIN hasheado (bcrypt)
3. Genera JWT con: user_id, tenant_id, role_id, permissions[]
4. JWT expires en N horas (configurable por tenant)
5. Frontend almacena JWT en httpOnly cookie + memory
6. Timeout de inactividad → logout automático (configurable)
```

### JWT Payload:
```json
{
  "sub": "user_uuid",
  "tenant_id": "tenant_uuid",
  "role": "cashier",
  "permissions": ["sale.create", "sale.read", "product.read"],
  "exp": 1712345678,
  "iat": 1712342078
}
```

### Seguridad:
- bcrypt para PINs (cost factor 10+)
- JWT firmado con RS256 (pares de llaves)
- Rate limit: 5 intentos fallidos → bloqueo 5 minutos
- Auditoría: cada login/logout se registra en audit_logs
- Refresh token opcional para sesiones largas (admin)

### Autenticación alternativa (Fase 2):
- Email + password para admin
- 2FA (TOTP) para operaciones críticas

---

## 5. Estrategia de Permisos

### Modelo RBAC (Role-Based Access Control):

```
tenants
  └── roles (por tenant)
        └── role_permissions
              └── permissions (catálogo global)
```

### Permisos Atómicos:

| Código | Descripción |
|--------|-------------|
| `sale.create` | Crear venta |
| `sale.read` | Consultar ventas |
| `sale.cancel` | Cancelar venta |
| `sale.refund` | Devolución |
| `sale.price_override` | Modificar precio en venta |
| `product.create` | Crear producto |
| `product.update` | Actualizar producto |
| `product.delete` | Eliminar producto |
| `product.read_cost` | Ver costo |
| `inventory.read` | Consultar inventario |
| `inventory.transfer` | Transferir inventario |
| `inventory.adjust` | Ajustar inventario |
| `cashier.open` | Abrir caja |
| `cashier.close` | Cerrar caja |
| `cashier.in` | Ingreso efectivo |
| `cashier.out` | Salida efectivo |
| `quotation.create` | Crear cotización |
| `quotation.convert` | Convertir cotización a venta |
| `customer.create` | Crear cliente |
| `customer.update` | Actualizar cliente |
| `report.read` | Ver reportes |
| `config.read` | Ver configuración |
| `config.update` | Modificar configuración |
| `user.create` | Crear usuario |
| `user.update` | Actualizar usuario |
| `user.delete` | Eliminar usuario |
| `audit.read` | Ver auditoría |
| `override.pin` | Override administrativo |

### Roles Semilla:

| Role | Permisos clave |
|------|---------------|
| admin | TODO |
| supervisor | sale.cancel, sale.refund, cashier.*, report.*, override.pin |
| cashier | sale.create, sale.read, product.read, customer.create, quotation.create, cashier.open/close |

### Override Administrativo:
- Operaciones críticas requieren PIN de admin
- Frontend muestra modal "Ingrese PIN de autorización"
- Backend valida contra usuario con permiso `override.pin`
- Se registra en audit_log con: `{ action, user, authorized_by, timestamp }`

---

## 6. Estrategia de Folios Únicos

### Regla Crítica:
> Dos cajas JAMÁS compartirán el mismo consecutivo.

### Implementación:

```sql
CREATE TABLE folio_controls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    branch_id UUID NOT NULL REFERENCES branches(id),
    cash_register_id UUID NOT NULL REFERENCES cash_registers(id),
    document_type VARCHAR(10) NOT NULL,  -- VTA, COT, DEV, etc.
    prefix VARCHAR(10) NOT NULL,          -- VTA-, COT-, DEV-
    current_number INTEGER NOT NULL DEFAULT 0,
    next_number INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, branch_id, cash_register_id, document_type)
);
```

### Generación Folio (Backend, Transaccional):

```python
async def next_folio(
    session: AsyncSession,
    tenant_id: UUID,
    branch_id: UUID,
    cash_register_id: UUID,
    document_type: str
) -> str:
    # Usa UPDATE ... RETURNING para atomicidad
    result = await session.execute(
        text("""
            UPDATE folio_controls
            SET current_number = next_number,
                next_number = next_number + 1,
                updated_at = NOW()
            WHERE tenant_id = :tenant_id
              AND branch_id = :branch_id
              AND cash_register_id = :cash_register_id
              AND document_type = :document_type
            RETURNING prefix, current_number
        """),
        {
            "tenant_id": tenant_id,
            "branch_id": branch_id,
            "cash_register_id": cash_register_id,
            "document_type": document_type
        }
    )
    row = result.fetchone()
    prefix, number = row.prefix, row.current_number
    return f"{prefix}{number:06d}"
```

### Ejemplo Folios:
| Tipo | Formato |
|------|---------|
| Venta | VTA-000145 |
| Cotización | COT-000211 |
| Devolución | DEV-000012 |
| Corte de caja | CORTE-000045 |

---

## 7. Estrategia de Inventario Transaccional

### Modelo:

```sql
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    product_id UUID NOT NULL REFERENCES products(id),
    warehouse_id UUID REFERENCES warehouses(id),
    location_id UUID REFERENCES locations(id),
    quantity DECIMAL(12, 4) NOT NULL DEFAULT 0,
    min_stock DECIMAL(12, 4) DEFAULT 0,
    max_stock DECIMAL(12, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, product_id, warehouse_id, location_id)
);
```

### Reglas de Descuento:

```
Venta en Caja 1 (Sucursal Norte):
  → Descuenta de inventory WHERE product_id=X AND location_id=Caja1

Venta en Caja 2 (Sucursal Norte):
  → Descuenta de inventory WHERE product_id=X AND location_id=Caja2

Transferencia de Almacén a Caja:
  → INSERT/UPDATE inventory con location_id destino
  → Ambos cambios en una transacción
```

### Validación Stock Negativo:

```python
async def validate_stock(
    session: AsyncSession,
    tenant_id: UUID,
    items: list[SaleItemCreate],
    location_id: UUID
) -> bool:
    for item in items:
        result = await session.execute(
            text("""
                SELECT quantity FROM inventory
                WHERE tenant_id = :tenant_id
                  AND product_id = :product_id
                  AND location_id = :location_id
                FOR UPDATE  -- LOCK ROW!
            """),
            {"tenant_id": tenant_id, "product_id": item.product_id, "location_id": location_id}
        )
        row = result.fetchone()
        if row is None or row.quantity < item.quantity:
            return False
    return True
```

### Transacción de Venta (Atómica):

```python
async def create_sale(session, tenant_id, data):
    async with session.begin():  # Transacción SQL
        # 1. Validar stock (SELECT ... FOR UPDATE)
        # 2. Generar folio (UPDATE folio_controls)
        # 3. Crear sale + sale_items
        # 4. Descontar inventory
        # 5. Registrar payment(s)
        # 6. Registrar audit_log
        # 7. Commit (todo o nada)
```

---

## 8. Módulos del Sistema

### Core Modules (shared/):
```
core/
  ├── __init__.py
  ├── config.py              # Settings (pydantic-settings)
  ├── security.py            # JWT, bcrypt, PIN
  ├── tenant.py              # Tenant context middleware
  ├── permissions.py         # RBAC engine
  ├── audit.py               # Audit logger
  ├── folios.py              # Folio engine
  ├── payments.py            # Payment processing
  ├── database.py            # AsyncSQLAlchemy engine
  └── models/
       ├── base.py           # DeclarativeBase + TimestampMixin
       ├── tenant.py
       ├── user.py
       ├── role.py
       └── ... (shared models)
```

### Feature Modules:
```
modules/
  ├── auth/
  │   ├── router.py
  │   ├── service.py
  │   ├── repository.py
  │   └── schemas.py
  ├── products/
  │   ├── router.py
  │   ├── service.py
  │   ├── repository.py
  │   └── schemas.py
  ├── inventory/
  │   ├── router.py
  │   ├── service.py
  │   ├── repository.py
  │   └── schemas.py
  ├── sales/
  │   ├── router.py
  │   ├── service.py
  │   ├── repository.py
  │   └── schemas.py
  ├── quotations/
  ├── customers/
  ├── cash_register/
  ├── reports/
  ├── audit/
  └── integrations/
```

---

## 9. Integración Hardware POS

### Capas de Integración:

```
Frontend (JS)
    │
    ├── QZ Tray (WebSocket local)
    │     ├── Impresora térmica (ESC/POS)
    │     ├── Cajón de dinero (ESC/POS)
    │     └── Impresora etiquetas (ZPL)
    │
    ├── Web Serial API (navegador)
    │     └── Escáner código barras USB HID
    │
    └── Terminales Bancarias (API)
          ├── Clip
          ├── Mercado Pago
          ├── Openpay
          ├── Conekta
          └── Stripe
```

### Estrategia:

1. **QZ Tray**: Comunicación vía WebSocket local (localhost). El frontend se conecta a QZ Tray para impresión térmica y apertura de cajón. QZ Tray maneja el ESC/POS nativo.

2. **Escáner USB HID**: Se comporta como teclado. El input del escáner termina con `\r` o `\n`. Frontend detecta entrada rápida vs tecleo humano y ejecuta búsqueda automática.

3. **Terminales Bancarias**: Integración vía APIs REST de cada proveedor. El backend genera el cargo, la terminal procesa, el backend confirma.

---

## 10. Esquema de Directorio Completo

```
fixit-pos/
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router
│   │   │   ├── (auth)/           # Login page
│   │   │   ├── (dashboard)/      # POS, caja, productos...
│   │   │   └── api/              # Next.js API routes (proxy)
│   │   ├── components/
│   │   │   ├── ui/              # shadcn/ui components
│   │   │   ├── pos/             # POS screen components
│   │   │   ├── cash-register/   # Caja components
│   │   │   └── shared/          # Shared components
│   │   ├── lib/
│   │   │   ├── api-client.ts    # Axios/fetch wrapper
│   │   │   ├── auth.ts          # JWT handling
│   │   │   └── utils.ts         # Utility functions
│   │   ├── hooks/
│   │   └── types/
│   ├── tailwind.config.ts
│   ├── next.config.js
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── products/
│   │   │   ├── inventory/
│   │   │   ├── sales/
│   │   │   ├── quotations/
│   │   │   ├── customers/
│   │   │   ├── cash_register/
│   │   │   ├── reports/
│   │   │   └── audit/
│   │   ├── main.py
│   │   └── dependencies.py
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── docs/
│   └── architecture.md
│
├── .gitignore
└── README.md
```

---

## 11. Principios de Diseño

| Principio | Aplicación |
|-----------|-----------|
| **Backend Authoritative** | Stock, folios, pagos, caja, permisos — todo se valida en backend |
| **Transacciones SQL** | Ventas = 1 transacción (sale + inventory + payment + folio) |
| **Multi-tenant Day 1** | `tenant_id` en TODAS las tablas desde el inicio |
| **No sobreingeniería** | Modular monolith, PostgreSQL, sin Kafka/K8s/microservicios |
| **API-first** | Frontend consume REST API; misma API para integraciones externas |
| **Audit Everything** | Toda acción crítica se registra con quién, cuándo, qué cambió |
| **Idempotencia** | Endpoints de venta/pago soportan idempotency_key |
| **Fail Fast** | Validaciones tempranas, mensajes de error claros en español |

---

## 12. Resumen para Implementación

| Etapa | Prioridad |
|-------|-----------|
| 1. DB Schema (PostgreSQL) | 🔴 Inmediata |
| 2. Backend Auth + Products + Inventory | 🔴 Inmediata |
| 3. Backend Sales + Payments + Folios | 🔴 Inmediata |
| 4. Frontend POS Screen + Caja | 🔴 Inmediata |
| 5. Frontend Products + Dashboard | 🟡 Media |
| 6. Cotizaciones + Clientes | 🟡 Media |
| 7. Hardware POS (QZ Tray, ESC/POS) | 🟢 Después |
| 8. Optimización UX (shortcuts, multitabs) | 🟢 Después |
