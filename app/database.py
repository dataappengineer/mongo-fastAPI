"""
Database connection module for MongoDB.
Provides connection configuration that can work with both Docker and external MongoDB,
with structured logging and detailed diagnostics.
"""
import os
import re
import time
import logging
from typing import Dict, Any, Tuple
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.uri_parser import parse_uri
from dotenv import load_dotenv

from app.logging_config import diagnose_mongo_error

# Load environment variables
load_dotenv()

logger = logging.getLogger("app.database")


def get_sanitized_uri(uri: str) -> str:
    """Mask credentials in MongoDB connection URI for safe logging."""
    if not uri:
        return ""
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", uri)


# MongoDB connection settings
MONGO_URI = os.getenv("MONGO_URI", "").strip()
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_DB = os.getenv("MONGO_DB", "testdb")
MONGO_USER = os.getenv("MONGO_USER", "")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "5000"))
MONGO_TLS_ENABLED = False
MONGO_NODES = []

# If MONGO_URI is defined, parse parameters and derive defaults
if MONGO_URI:
    try:
        _parsed = parse_uri(MONGO_URI)
        _uri_db = _parsed.get("database")
        _env_db = os.getenv("MONGO_DB")
        # Use URI database if MONGO_DB was not explicitly overridden
        if _uri_db and (_env_db is None or _env_db == "" or _env_db == "testdb"):
            MONGO_DB = _uri_db
        
        if _parsed.get("username"):
            MONGO_USER = _parsed.get("username")
            
        if _parsed.get("nodelist"):
            MONGO_NODES = [f"{h}:{p}" for h, p in _parsed["nodelist"]]
            MONGO_HOST = ",".join(MONGO_NODES)
            MONGO_PORT = _parsed["nodelist"][0][1]
            
        _opts = _parsed.get("options", {})
        MONGO_TLS_ENABLED = bool(_opts.get("tls") or _opts.get("ssl"))
    except Exception as _e:
        logger.warning("⚠️ Impossibile analizzare MONGO_URI con uri_parser: %s", str(_e))

# Global MongoDB client
_client = None


def get_connection_summary() -> Dict[str, Any]:
    """Return a sanitized dictionary summarizing the current MongoDB configuration."""
    return {
        "uri_configured": bool(MONGO_URI),
        "sanitized_uri": get_sanitized_uri(MONGO_URI) if MONGO_URI else None,
        "nodes": MONGO_NODES if MONGO_NODES else [f"{MONGO_HOST}:{MONGO_PORT}"],
        "host": MONGO_HOST,
        "port": MONGO_PORT,
        "database": MONGO_DB,
        "user_configured": bool(MONGO_USER),
        "username": MONGO_USER if MONGO_USER else None,
        "tls_enabled": MONGO_TLS_ENABLED,
        "timeout_ms": MONGO_TIMEOUT_MS,
    }


def get_mongo_client() -> MongoClient:
    """
    Get or create MongoDB client instance with timeout and retry settings.
    Supports either MONGO_URI (full connection string with TLS/ReplicaSet)
    or legacy individual variables (MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PASSWORD).
    
    Returns:
        MongoClient: MongoDB client connection
    """
    global _client
    
    if _client is None:
        if MONGO_URI:
            sanitized = get_sanitized_uri(MONGO_URI)
            logger.info(
                "🔌 Inizializzazione client MongoDB da MONGO_URI (TLS=%s): %s (db='%s', timeout=%dms)",
                MONGO_TLS_ENABLED,
                sanitized,
                MONGO_DB,
                MONGO_TIMEOUT_MS,
            )
            _client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=MONGO_TIMEOUT_MS,
                connectTimeoutMS=MONGO_TIMEOUT_MS,
                socketTimeoutMS=MONGO_TIMEOUT_MS,
            )
        else:
            auth_info = f"user='{MONGO_USER}'" if MONGO_USER else "no-auth"
            logger.info(
                "🔌 Inizializzazione client MongoDB legacy: host='%s', port=%d, db='%s', auth=%s, timeout=%dms",
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
    if MONGO_URI:
        try:
            default_db = client.get_default_database()
            if default_db is not None:
                return default_db
        except Exception:
            pass
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
    target_display = get_sanitized_uri(MONGO_URI) if MONGO_URI else f"{MONGO_HOST}:{MONGO_PORT}"
    try:
        db = get_database()
        db.command("ping")
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.debug("✅ Ping MongoDB completato in %.2f ms su %s", latency_ms, target_display)
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
            "   Target: %s (db=%s, user=%s)\n"
            "   Dettaglio: %s\n"
            "   Suggerimento: %s",
            diag["error_category"],
            diag["summary"],
            target_display,
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
