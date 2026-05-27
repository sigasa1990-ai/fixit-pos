import logging
import logging.config
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AppException, NotFoundException
from app.core.middleware import (
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.database import engine, get_db
from app.dependencies import get_current_tenant_id
from app.modules.auth.router import router as auth_router
from app.modules.products.router import router as products_router
from app.modules.inventory.router import router as inventory_router
from app.modules.customers.router import router as customers_router
from app.modules.cash_register.router import router as cash_register_router
from app.modules.sales.router import router as sales_router
from app.modules.quotations.router import router as quotations_router

settings = get_settings()

logging.config.fileConfig("app/logging.conf", disable_existing_loggers=False)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FIXIT POS API", extra={"version": settings.APP_VERSION})
    # Verify database connectivity on startup
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("Database connection verified")
    except Exception as e:
        logger.error("Database connection failed", extra={"error": str(e)})
        raise
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
