"""
Database connection module for MongoDB.
Provides connection configuration that can work with both Docker and external MongoDB,
with structured logging and detailed diagnostics.
"""
import os
import time
import logging
from typing import Dict, Any, Tuple
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv

from app.logging_config import diagnose_mongo_error

# Load environment variables
load_dotenv()

logger = logging.getLogger("app.database")

# MongoDB connection settings
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_DB = os.getenv("MONGO_DB", "testdb")
MONGO_USER = os.getenv("MONGO_USER", "")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "5000"))

# Global MongoDB client
_client = None


def get_connection_summary() -> Dict[str, Any]:
    """Return a sanitized dictionary summarizing the current MongoDB configuration."""
    return {
        "host": MONGO_HOST,
        "port": MONGO_PORT,
        "database": MONGO_DB,
        "user_configured": bool(MONGO_USER),
        "username": MONGO_USER if MONGO_USER else None,
        "timeout_ms": MONGO_TIMEOUT_MS,
    }


def get_mongo_client() -> MongoClient:
    """
    Get or create MongoDB client instance with timeout and retry settings.
    
    Returns:
        MongoClient: MongoDB client connection
    """
    global _client
    
    if _client is None:
        auth_info = f"user='{MONGO_USER}'" if MONGO_USER else "no-auth"
        logger.info(
            "🔌 Inizializzazione client MongoDB: host='%s', port=%d, db='%s', auth=%s, timeout=%dms",
            MONGO_HOST,
            MONGO_PORT,
            MONGO_DB,
            auth_info,
            MONGO_TIMEOUT_MS,
        )
        
        # Build connection string
        if MONGO_USER and MONGO_PASSWORD:
            connection_string = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/"
        else:
            connection_string = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
        
        _client = MongoClient(
            connection_string,
            serverSelectionTimeoutMS=MONGO_TIMEOUT_MS,
            connectTimeoutMS=MONGO_TIMEOUT_MS,
            socketTimeoutMS=MONGO_TIMEOUT_MS,
        )
        
    return _client


def get_database() -> Database:
    """
    Get the MongoDB database instance.
    
    Returns:
        Database: MongoDB database object
    """
    client = get_mongo_client()
    return client[MONGO_DB]


def check_mongo_connection() -> Tuple[bool, float, Dict[str, Any], Any]:
    """
    Perform a live ping command to verify database connectivity.
    
    Returns:
        Tuple[bool, float, dict, Optional[str]]:
            - is_connected (bool)
            - latency_ms (float)
            - summary_info (dict)
            - error_diagnostic (dict or None)
    """
    summary = get_connection_summary()
    start_time = time.time()
    try:
        db = get_database()
        db.command("ping")
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.debug("✅ Ping MongoDB completato in %.2f ms su %s:%d", latency_ms, MONGO_HOST, MONGO_PORT)
        return True, latency_ms, summary, None
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        diag = diagnose_mongo_error(
            e,
            host=MONGO_HOST,
            port=MONGO_PORT,
            database=MONGO_DB,
            user=MONGO_USER,
        )
        logger.error(
            "❌ [MONGODB ERROR] Fallimento connessione/operazione:\n"
            "   Categoria: %s\n"
            "   Sommario: %s\n"
            "   Target: host=%s, port=%d, db=%s, user=%s\n"
            "   Dettaglio: %s\n"
            "   Suggerimento: %s",
            diag["error_category"],
            diag["summary"],
            MONGO_HOST,
            MONGO_PORT,
            MONGO_DB,
            MONGO_USER or "None",
            diag["details"],
            diag["actionable_hint"],
        )
        return False, latency_ms, summary, diag


def close_connection():
    """
    Close MongoDB connection.
    Call this on application shutdown.
    """
    global _client
    if _client is not None:
        logger.info("🛑 Chiusura connessione MongoDB...")
        _client.close()
        _client = None
        logger.info("✅ Connessione MongoDB chiusa con successo.")
