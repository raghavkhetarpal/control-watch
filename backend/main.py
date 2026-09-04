"""AWM ControlWatch - FastAPI Backend Application.

Investment Operations Risk & Control Monitoring Platform.
Educational/research implementation based on publicly available SEC data.
Does NOT replicate or represent Goldman Sachs' proprietary systems.
"""
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import structlog

from backend.database.connection import init_db, check_db_health

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("starting_application", version="1.0.0")
    try:
        init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
    yield
    logger.info("shutting_down_application")


app = FastAPI(
    title="AWM ControlWatch",
    description=(
        "Investment Operations Risk & Control Monitoring Platform. "
        "Educational/research implementation based on publicly available SEC data. "
        "Does NOT replicate or represent Goldman Sachs' proprietary systems, "
        "controls, data, or risk framework."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.1f}"
    return response


# Import and register routers
from backend.api.funds import router as funds_router
from backend.api.holdings import router as holdings_router
from backend.api.controls import router as controls_router
from backend.api.exceptions import router as exceptions_router
from backend.api.metrics import router as metrics_router
from backend.api.audit import router as audit_router
from backend.api.ai_routes import router as ai_router
from backend.api.ingestion_routes import router as ingestion_router

app.include_router(funds_router, prefix="/funds", tags=["Funds"])
app.include_router(holdings_router, prefix="/holdings", tags=["Holdings"])
app.include_router(controls_router, prefix="/controls", tags=["Controls"])
app.include_router(exceptions_router, prefix="/exceptions", tags=["Exceptions"])
app.include_router(metrics_router, tags=["Metrics"])
app.include_router(audit_router, prefix="/audit-events", tags=["Audit"])
app.include_router(ai_router, prefix="/ai", tags=["AI"])
app.include_router(ingestion_router, prefix="/ingestion", tags=["Ingestion"])


@app.get("/health", tags=["System"])
def health_check():
    """System health check endpoint."""
    db_health = check_db_health()
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "version": "1.0.0",
        "database": db_health,
        "ai_provider": os.environ.get("AI_PROVIDER", "none"),
    }
