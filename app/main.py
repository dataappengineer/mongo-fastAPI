"""
FastAPI main application with structured logging and comprehensive diagnostics.
"""
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError

from app.logging_config import setup_logging, diagnose_mongo_error
from app.database import (
    close_connection,
    check_mongo_connection,
    MONGO_HOST,
    MONGO_PORT,
    MONGO_DB,
    MONGO_USER,
)
from app.routers import collections, sql

# Initialize structured logging on import
setup_logging()
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events with diagnostics.
    """
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 Avvio FastAPI MongoDB REST API v1.0.0...")
    logger.info(
        "⚙️ Configurazione iniziale MongoDB: host='%s', port=%d, db='%s', user='%s'",
        MONGO_HOST,
        MONGO_PORT,
        MONGO_DB,
        MONGO_USER or "(no-auth)",
    )
    is_ok, latency, summary, err = check_mongo_connection()
    if is_ok:
        logger.info("✅ Connessione iniziale MongoDB: OK (latenza: %.2f ms)", latency)
    else:
        logger.warning(
            "⚠️ ATTENZIONE: Connessione iniziale MongoDB non riuscita su %s:%d! "
            "FastAPI si avvia comunque, ma le chiamate database falliranno finché MongoDB non sarà raggiungibile.",
            MONGO_HOST,
            MONGO_PORT,
        )
    logger.info("📊 FastAPI REST API pronta all'uso.")
    logger.info("=" * 60)
    yield
    # Shutdown
    logger.info("🛑 Spegnimento applicazione...")
    close_connection()
    logger.info("✅ Applicazione arrestata correttamente.")


app = FastAPI(
    title="MongoDB REST API",
    description="REST API for MongoDB collections with metadata, data retrieval and enhanced diagnostics",
    version="1.0.0",
    lifespan=lifespan
)

# Global Exception Handler for any uncaught PyMongoError
@app.exception_handler(PyMongoError)
async def pymongo_exception_handler(request: Request, exc: PyMongoError):
    diag = diagnose_mongo_error(
        exc,
        host=MONGO_HOST,
        port=MONGO_PORT,
        database=MONGO_DB,
        user=MONGO_USER,
    )
    logger.error(
        "❌ [UNCAUGHT PYMONGO ERROR on %s %s]:\n"
        "   Categoria: %s\n"
        "   Sommario: %s\n"
        "   Target: host=%s, port=%d, db=%s, user=%s\n"
        "   Dettaglio: %s\n"
        "   Suggerimento: %s",
        request.method,
        request.url.path,
        diag["error_category"],
        diag["summary"],
        MONGO_HOST,
        MONGO_PORT,
        MONGO_DB,
        MONGO_USER or "None",
        diag["details"],
        diag["actionable_hint"],
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": diag,
            "path": request.url.path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# Global Exception Handler for any uncaught generic Exception
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(
        "❌ [UNHANDLED SERVER ERROR on %s %s]: %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
        str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": {
                "error_category": "INTERNAL_SERVER_ERROR",
                "summary": f"Errore interno del server: {type(exc).__name__}",
                "details": str(exc),
                "actionable_hint": "Consulta i log del container per lo stack trace completo.",
            },
            "path": request.url.path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


# CORS middleware configuration for frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dss.regione.puglia.it",
        "https://dss-coll.regione.puglia.it",
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"https://.*\.regione\.puglia\.it",  # Consente tutti i sottodomini Regione Puglia
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(collections.router)
app.include_router(sql.router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "MongoDB REST API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "list_collections": "GET /collections/",
            "collection_metadata": "GET /collections/{collection_name}/metadata",
            "collection_data": "GET /collections/{collection_name}/data?page=1&page_size=20",
            "sql_validate": "POST /sql/validate",
        }
    }


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint with live MongoDB connection test.
    Used by Kubernetes liveness and readiness probes, and for rapid diagnostics.
    
    Returns:
        dict: Detailed health status, latency, target configuration and diagnostic error if unhealthy.
    """
    is_connected, latency_ms, config_summary, error_diag = check_mongo_connection()
    now_iso = datetime.now(timezone.utc).isoformat()
    
    if is_connected:
        return {
            "status": "healthy",
            "mongodb": "connected",
            "database": config_summary["database"],
            "host": config_summary["host"],
            "port": config_summary["port"],
            "auth_configured": config_summary["user_configured"],
            "latency_ms": latency_ms,
            "version": "1.0.0",
            "timestamp": now_iso,
        }
    else:
        return {
            "status": "unhealthy",
            "mongodb": "disconnected",
            "database": config_summary["database"],
            "host": config_summary["host"],
            "port": config_summary["port"],
            "auth_configured": config_summary["user_configured"],
            "latency_ms": latency_ms,
            "version": "1.0.0",
            "timestamp": now_iso,
            "diagnostic_error": error_diag,
        }
