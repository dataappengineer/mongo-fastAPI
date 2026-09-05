"""
Centralized logging configuration and diagnostic error formatters.
"""
import logging
import sys
import os
from typing import Dict, Any, Optional
from pymongo.errors import (
    PyMongoError,
    ServerSelectionTimeoutError,
    OperationFailure,
    NetworkTimeout,
    ConnectionFailure,
    ConfigurationError,
)


def setup_logging():
    """
    Configure structured and verbose logging for the FastAPI application.
    Ensures logs are cleanly formatted on stdout for Docker and Kubernetes.
    """
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    log_format = (
        "%(asctime)s [%(levelname)s] [%(name)s] "
        "[%(filename)s:%(lineno)d]: %(message)s"
    )

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Set specific levels for application loggers
    logging.getLogger("app").setLevel(log_level)
    logging.getLogger("app.database").setLevel(log_level)
    logging.getLogger("app.routers").setLevel(log_level)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


logger = logging.getLogger("app.diagnostics")


def diagnose_mongo_error(
    error: Exception,
    host: str,
    port: int,
    database: str,
    user: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze a MongoDB / PyMongo error and produce an explicit, highly verbose
    diagnostic dictionary with root cause, connection details, and actionable hints.
    """
    error_str = str(error)
    error_lower = error_str.lower()
    has_auth = bool(user)

    # 1. Authentication Failures (Check both OperationFailure and wrapped string messages)
    if "authentication failed" in error_lower or "auth error" in error_lower or "code': 18" in error_str or "authenticationfailed" in error_lower:
        return {
            "error_category": "MONGODB_AUTHENTICATION_FAILED",
            "summary": f"Autenticazione MongoDB fallita per l'utente '{user}' sul database '{database}' (host '{host}:{port}')",
            "details": error_str,
            "connection_target": {
                "host": host,
                "port": port,
                "database": database,
                "user": user,
                "auth_configured": True,
            },
            "actionable_hint": (
                "Credenziali MongoDB non valide. Verifica 'MONGO_USER' e 'MONGO_PASSWORD' nei Secret Kubernetes "
                "o nelle variabili d'ambiente. Assicurati che l'utente esista nel database specificato e che la password sia corretta."
            ),
        }

    # 2. Authorization Failures (Permission issues)
    if "not authorized" in error_lower or "unauthorized" in error_lower or "code': 13" in error_str:
        return {
            "error_category": "MONGODB_AUTHORIZATION_FAILED",
            "summary": f"L'utente '{user}' non possiede i permessi necessari sul database '{database}'",
            "details": error_str,
            "connection_target": {
                "host": host,
                "port": port,
                "database": database,
                "user": user,
            },
            "actionable_hint": (
                f"Assegna all'utente '{user}' i ruoli di lettura/scrittura sul database '{database}' "
                "(es. 'readWrite' o 'dbOwner') in MongoDB."
            ),
        }

    # 3. Connection / Timeout / Reachability Failures
    if isinstance(error, (ServerSelectionTimeoutError, ConnectionFailure, NetworkTimeout)) or "timed out" in error_lower or "name or service not known" in error_lower or "connection refused" in error_lower:
        return {
            "error_category": "MONGODB_CONNECTION_TIMEOUT",
            "summary": f"Impossibile connettersi al server MongoDB su '{host}:{port}'",
            "details": error_str,
            "connection_target": {
                "host": host,
                "port": port,
                "database": database,
                "user": user if has_auth else "None (No Auth)",
            },
            "actionable_hint": (
                f"Verifica che MongoDB sia attivo e raggiungibile all'host '{host}' sulla porta {port}. "
                "In Kubernetes, controlla il nome del Service K8s (es. 'mongodb.namespace.svc.cluster.local') "
                "e che le NetworkPolicy consentano il traffico sulla porta 27017."
            ),
        }

    # 4. Configuration Errors
    if isinstance(error, ConfigurationError):
        return {
            "error_category": "MONGODB_CONFIGURATION_ERROR",
            "summary": "Errore nella configurazione della connessione MongoDB",
            "details": error_str,
            "connection_target": {"host": host, "port": port, "database": database},
            "actionable_hint": "Verifica la sintassi della stringa di connessione e i parametri passati a PyMongo.",
        }

    # 5. Generic PyMongo / Unexpected Error
    return {
        "error_category": "MONGODB_GENERIC_ERROR",
        "summary": f"Errore MongoDB non classificato: {type(error).__name__}",
        "details": error_str,
        "connection_target": {
            "host": host,
            "port": port,
            "database": database,
            "user": user if has_auth else "None",
        },
        "actionable_hint": "Consulta i log completi di FastAPI e del server MongoDB per maggiori dettagli.",
    }
