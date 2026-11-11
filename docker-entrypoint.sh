#!/bin/sh
set -e

PORT="${PORT:-8443}"
WORKERS="${UVICORN_WORKERS:-4}"

# If a custom command was passed to the container, execute it directly
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# Auto-detect TLS certificates
if [ -f "/etc/tls/tls.crt" ] && [ -f "/etc/tls/tls.key" ]; then
    echo "🔒 Certificati TLS rilevati in /etc/tls - Avvio Uvicorn in HTTPS sulla porta ${PORT} con ${WORKERS} workers..."
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --ssl-certfile /etc/tls/tls.crt --ssl-keyfile /etc/tls/tls.key --workers "${WORKERS}"
else
    echo "ℹ️ Nessun certificato TLS rilevato in /etc/tls - Avvio Uvicorn in HTTP sulla porta 8000 con ${WORKERS} workers..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WORKERS}"
fi
