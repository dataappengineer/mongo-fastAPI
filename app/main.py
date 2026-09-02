"""
FastAPI main application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import close_connection
from app.routers import collections, sql


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    print("🚀 Starting FastAPI application...")
    print("📊 MongoDB REST API is ready")
    yield
    # Shutdown
    print("🛑 Shutting down application...")
    close_connection()
    print("✅ MongoDB connection closed")


app = FastAPI(
    title="MongoDB REST API",
    description="REST API for MongoDB collections with metadata and data retrieval",
    version="1.0.0",
    lifespan=lifespan
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


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "MongoDB REST API",
        "version": "1.0.0",
        "endpoints": {
            "list_collections": "GET /collections/",
            "collection_metadata": "GET /collections/{collection_name}/metadata",
            "collection_data": "GET /collections/{collection_name}/data?max_righe={n}"
        }
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint with MongoDB connection test.
    Used by Kubernetes liveness and readiness probes.
    
    Returns:
        dict: Status information including MongoDB connectivity
    """
    try:
        from app.database import get_database
        db = get_database()
        # Test MongoDB connection with ping command
        db.command("ping")
        return {
            "status": "healthy",
            "mongodb": "connected",
            "database": db.name,
            "version": "1.0.0"
        }
    except Exception as e:
        # Return 200 status but with error info
        # Kubernetes can parse the response body to determine health
        return {
            "status": "unhealthy",
            "mongodb": "disconnected",
            "error": str(e),
            "version": "1.0.0"
        }
