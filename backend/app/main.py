import logging
import logging.config
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AppException, NotFoundException
from app.core.middleware import (
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.database import engine, get_db, async_session_factory
from app.dependencies import get_current_tenant_id
from app.modules.auth.router import router as auth_router
from app.modules.products.router import router as products_router
from app.modules.inventory.router import router as inventory_router
from app.modules.customers.router import router as customers_router
from app.modules.cash_register.router import router as cash_register_router
from app.modules.sales.router import router as sales_router
from app.modules.quotations.router import router as quotations_router

settings = get_settings()

try:
    logging.config.fileConfig("app/logging.conf", disable_existing_loggers=False)
except Exception:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


async def seed_database():
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    async with async_session_factory() as db:
        try:
            existing = await db.execute(text("SELECT id FROM tenants LIMIT 1"))
            if existing.fetchone():
                logger.info("Seed data already exists, skipping")
                return
            logger.info("Creating seed data...")
            tid = (await db.execute(text(
                "INSERT INTO tenants (business_name, commercial_name, is_active) "
                "VALUES ('FixIT Soluciones', 'FixIT Soluciones', true) RETURNING id"
            ))).scalar()
            rid = (await db.execute(text(
                "INSERT INTO roles (tenant_id, name, role_type, description, is_system) "
                "VALUES (:tid, 'Administrador', 'admin', 'Rol administrador del sistema', true) RETURNING id",
            ), {"tid": tid})).scalar()
            pin_hash = pwd_context.hash("1234")
            uid = (await db.execute(text(
                "INSERT INTO users (tenant_id, role_id, username, pin_hash, full_name, is_active) "
                "VALUES (:tid, :rid, 'admin', :pin, 'Administrador', true) RETURNING id",
            ), {"tid": tid, "rid": rid, "pin": pin_hash})).scalar()
            perms = await db.execute(text("SELECT id FROM permissions"))
            for row in perms.fetchall():
                await db.execute(text(
                    "INSERT INTO role_permissions (role_id, permission_id, tenant_id) "
                    "VALUES (:rid, :pid, :tid) ON CONFLICT DO NOTHING"
                ), {"rid": rid, "pid": row[0], "tid": tid})
            bid = (await db.execute(text(
                "INSERT INTO branches (tenant_id, code, name, is_active) "
                "VALUES (:tid, 'PRINCIPAL', 'Sucursal Principal', true) RETURNING id"
            ), {"tid": tid})).scalar()
            await db.execute(text(
                "INSERT INTO user_branches (user_id, branch_id, tenant_id, is_default) "
                "VALUES (:uid, :bid, :tid, true)"
            ), {"uid": uid, "bid": bid, "tid": tid})
            wid = (await db.execute(text(
                "INSERT INTO warehouses (tenant_id, branch_id, code, name, is_active) "
                "VALUES (:tid, :bid, 'PRINCIPAL', 'Almacen Principal', true) RETURNING id"
            ), {"tid": tid, "bid": bid})).scalar()
            await db.execute(text(
                "INSERT INTO locations (tenant_id, warehouse_id, branch_id, code, name, is_active) "
                "VALUES (:tid, :wid, :bid, 'PRINCIPAL', 'Ubicacion Principal', true) RETURNING id"
            ), {"tid": tid, "wid": wid, "bid": bid})
            await db.commit()
            logger.info("Seed data created: admin / 1234")
        except Exception as e:
            await db.rollback()
            logger.warning(f"Seed failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FIXIT POS API", extra={"version": settings.APP_VERSION})
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed")
    except Exception as e:
        logger.warning(f"Migrations failed: {e}")
    await seed_database()
    yield
    logger.info("Shutting down FIXIT POS API")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware order matters: CorrelationID first, then Security, then Logging, then CORS
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    expose_headers=settings.CORS_EXPOSE_HEADERS,
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning(
        f"App exception: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "correlation_id": getattr(request.state, "correlation_id", None)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "correlation_id": getattr(request.state, "correlation_id", None),
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Error interno del servidor",
            "correlation_id": getattr(request.state, "correlation_id", None),
        },
    )


@app.get("/debug/db")
async def debug_db(db: AsyncSession = Depends(get_db)):
    results = {}
    tables = ["tenants", "permissions", "roles", "users", "user_sessions", "audit_logs", "role_permissions"]
    for table in tables:
        try:
            r = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            results[table] = {"exists": True, "count": r.scalar()}
        except Exception as e:
            results[table] = {"exists": False, "error": str(e)}
    try:
        r = await db.execute(text("SELECT version FROM alembic_version"))
        results["alembic_version"] = r.scalar()
    except Exception as e:
        results["alembic_version"] = str(e)
    return results


@app.post("/debug/migrate")
async def debug_migrate():
    import subprocess, sys
    try:
        r = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True, text=True, timeout=60,
        )
        return {
            "returncode": r.returncode,
            "stdout": r.stdout,
            "stderr": r.stderr,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "healthy" if db_ok else "degraded",
        "version": settings.APP_VERSION,
        "database": "connected" if db_ok else "disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/tenant/info")
async def tenant_info(
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
):
    result = await db.execute(
        text("""
            SELECT business_name, commercial_name, rfc, address, phone,
                   ticket_header, ticket_footer, ticket_policies,
                   logo_url, primary_color, secondary_color
            FROM tenants WHERE id = :id
        """),
        {"id": tenant_id},
    )
    row = result.fetchone()
    if not row:
        raise NotFoundException("Tenant no encontrado")
    return dict(row._mapping)


@app.get("/api/v1/dashboard/summary")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_current_tenant_id),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    today = await db.execute(
        text("""
            SELECT
                COALESCE(COUNT(*), 0) as sale_count,
                COALESCE(SUM(total), 0) as sale_total
            FROM sales
            WHERE tenant_id = :tid
              AND created_at >= :today
              AND status = 'completed'
              AND deleted_at IS NULL
        """),
        {"tid": tenant_id, "today": today_start},
    )
    today_row = today.fetchone()

    month = await db.execute(
        text("""
            SELECT COALESCE(SUM(total), 0) as month_total
            FROM sales
            WHERE tenant_id = :tid
              AND created_at >= :month_start
              AND status = 'completed'
              AND deleted_at IS NULL
        """),
        {"tid": tenant_id, "month_start": month_start},
    )
    month_row = month.fetchone()

    low_stock = await db.execute(
        text("""
            SELECT COUNT(*) FROM inventory
            WHERE tenant_id = :tid AND quantity <= min_stock AND min_stock > 0
        """),
        {"tid": tenant_id},
    )
    low_row = low_stock.fetchone()

    return {
        "today_sales": float(today_row.sale_total),
        "today_count": today_row.sale_count,
        "today_tickets": today_row.sale_count,
        "low_stock_count": low_row.count,
        "month_sales": float(month_row.month_total),
    }


app.include_router(auth_router)
app.include_router(products_router)
app.include_router(inventory_router)
app.include_router(customers_router)
app.include_router(cash_register_router)
app.include_router(sales_router)
app.include_router(quotations_router)
