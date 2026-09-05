# Guida Operativa: Verbocità Log e Diagnostica Avanzata Errori
## FastAPI MongoDB REST API - Versione 1.0.1

**Repository**: [https://github.com/dataappengineer/mongo-fastAPI/tree/main](https://github.com/dataappengineer/mongo-fastAPI/tree/main)  
**Data Rilascio**: Settembre 2026  
**Autore**: Giovanni Brucoli (PhD)  
**Destinatari**: Team di Sviluppo, DevOps (Valentino Calcagno), Project Manager (Claudio, Simona)

---

## 📋 Indice

1. [Obiettivo dell'Aggiornamento v1.0.1](#1-obiettivo-dellaggiornamento-v101)
2. [Confronto Prima vs Dopo](#2-confronto-prima-vs-dopo)
3. [Tipologie di Errori Gestiti e Diagnosticati](#3-tipologie-di-errori-gestiti-e-diagnosticati)
4. [Esempi Pratici di Diagnostica Live](#4-esempi-pratici-di-diagnostica-live)
   - [Caso A: Credenziali Errate (Authentication Failed)](#caso-a-credenziali-errate-authentication-failed)
   - [Caso B: Host/Porta Non Raggiungibile (Connection Timeout)](#caso-b-hostporta-non-raggiungibile-connection-timeout)
   - [Caso C: Collezione Inesistente (404 con Elenco Collezioni)](#caso-c-collezione-inesistente-404-con-elenco-collezioni)
5. [Il Nuovo Endpoint `/health`](#5-il-nuovo-endpoint-health)
6. [Istruzioni per il Deploy dell'Immagine Docker v1.0.1](#6-istruzioni-per-il-deploy-dellimmagine-docker-v101)

---

## 1. Obiettivo dell'Aggiornamento v1.0.1

Durante i test in ambienti di collaudo/produzione su Kubernetes, si verificano frequentemente problemi di configurazione (es. Secret disallineati, password modificate, service name errati). Nella versione precedente:
- Uvicorn stampava solo `500 Internal Server Error` senza dettagli a schermo.
- L'Edge Layer/Gateway riceveva un errore generico e rispondeva con `Content-Length: 0`.

Nella **versione 1.0.1** abbiamo introdotto:
1. **Logging Strutturato su stdout**: Ogni chiamata, eccezione e timeout viene stampata a schermo nei container logs (`kubectl logs`) con categorizzazione chiara (`MONGODB_AUTHENTICATION_FAILED`, `MONGODB_CONNECTION_TIMEOUT`, ecc.), target di connessione e **suggerimento operativo per la risoluzione**.
2. **Payload di Risposta Diagnostico**: L'API restituisce un oggetto JSON ricco con dettagli, sommario e `actionable_hint`.
3. **Endpoint `/health` Potenziato**: Esegue un ping MongoDB in tempo reale con latenza e diagnosi automatica.
4. **Timeout di Connessione Rapido (`MONGO_TIMEOUT_MS`)**: Default a 5000 ms per evitare che l'applicazione rimanga appesa per 30 secondi prima di restituire l'errore.
5. **Supporto WebSocket Completo**: Installato `websockets` per eliminare i warning Uvicorn sullo Swagger.

---

## 2. Confronto Prima vs Dopo

### ❌ Prima (Versione 1.0.0)
* **Log del Container (`kubectl logs`)**:
  ```text
  INFO: 10.200.3.186:37732 - "GET /collections/C_DR_WLF_WELFARE_CompFam/metadata HTTP/1.1" 500 Internal Server Error
  ```
  *(Zero spiegazioni, impossibile capire se la colpa fosse della password, dell'host o della query).*

* **Risposta HTTP**:
  ```json
  {"detail": "Database error: Authentication failed."}
  ```

---

### ✅ Dopo (Versione 1.0.1)
* **Log del Container (`kubectl logs`)**:
  ```text
  2026-09-05 13:15:18 [ERROR] [app.database] [database.py:120]: ❌ [MONGODB ERROR] Fallimento connessione/operazione:
     Categoria: MONGODB_AUTHENTICATION_FAILED
     Sommario: Autenticazione MongoDB fallita per l'utente 'admin_user' sul database 'dss_db' (host 'mongodb:27017')
     Target: host=mongodb, port=27017, db=dss_db, user=admin_user
     Dettaglio: Authentication failed., full error: {'ok': 0.0, 'errmsg': 'Authentication failed.', 'code': 18}
     Suggerimento: Credenziali MongoDB non valide. Verifica 'MONGO_USER' e 'MONGO_PASSWORD' nei Secret Kubernetes o nelle variabili d'ambiente. Assicurati che l'utente esista nel database specificato e che la password sia corretta.
  ```

* **Risposta HTTP JSON**:
  ```json
  {
    "detail": {
      "error_category": "MONGODB_AUTHENTICATION_FAILED",
      "summary": "Autenticazione MongoDB fallita per l'utente 'admin_user' sul database 'dss_db' (host 'mongodb:27017')",
      "details": "Authentication failed., full error: {'ok': 0.0, 'errmsg': 'Authentication failed.', 'code': 18}",
      "connection_target": {
        "host": "mongodb",
        "port": 27017,
        "database": "dss_db",
        "user": "admin_user",
        "auth_configured": true
      },
      "actionable_hint": "Credenziali MongoDB non valide. Verifica 'MONGO_USER' e 'MONGO_PASSWORD' nei Secret Kubernetes o nelle variabili d'ambiente. Assicurati che l'utente esista nel database specificato e che la password sia corretta."
    }
  }
  ```

---

## 3. Tipologie di Errori Gestiti e Diagnosticati

Il modulo `app/logging_config.py` riconosce e mappa automaticamente:

| Categoria Errore | Causa Reale | Azione Suggerita nel Log |
|---|---|---|
| **`MONGODB_AUTHENTICATION_FAILED`** | Username o password errati in K8s Secret | Aggiornare Secret con le credenziali corrette dell'utente MongoDB. |
| **`MONGODB_AUTHORIZATION_FAILED`** | Utente autenticato ma senza permessi sulla collezione/DB | Assegnare il ruolo `readWrite` o `dbOwner` su MongoDB. |
| **`MONGODB_CONNECTION_TIMEOUT`** | Host/porta errati o NetworkPolicy K8s bloccata | Verificare `MONGO_HOST`, porta 27017 e Service DNS di Kubernetes. |
| **`COLLECTION_NOT_FOUND`** | Nome collezione non presente nel database | Restituisce 404 con l'**elenco completo delle collezioni esistenti**. |
| **`MONGODB_CONFIGURATION_ERROR`** | Parametri URI di connessione malformati | Correggere sintassi delle variabili d'ambiente. |

---

## 4. Esempi Pratici di Diagnostica Live

### Caso A: Credenziali Errate (Authentication Failed)

**Richiesta**:
```bash
curl -i -X GET "http://[HOST]/collections/"
```
**Risposta HTTP (500)**:
```json
{
  "detail": {
    "error_category": "MONGODB_AUTHENTICATION_FAILED",
    "summary": "Autenticazione MongoDB fallita per l'utente 'invalid_user' sul database 'testdb' (host 'mongodb:27017')",
    "details": "Authentication failed., full error: {'ok': 0.0, 'errmsg': 'Authentication failed.', 'code': 18, 'codeName': 'AuthenticationFailed'}",
    "connection_target": {
      "host": "mongodb",
      "port": 27017,
      "database": "testdb",
      "user": "invalid_user",
      "auth_configured": true
    },
    "actionable_hint": "Credenziali MongoDB non valide. Verifica 'MONGO_USER' e 'MONGO_PASSWORD' nei Secret Kubernetes o nelle variabili d'ambiente."
  }
}
```

---

### Caso B: Host/Porta Non Raggiungibile (Connection Timeout)

**Richiesta**:
```bash
curl -i -X GET "http://[HOST]/collections/"
```
**Risposta HTTP (500)**:
```json
{
  "detail": {
    "error_category": "MONGODB_CONNECTION_TIMEOUT",
    "summary": "Impossibile connettersi al server MongoDB su 'mongodb-invalid:27017'",
    "details": "mongodb-invalid:27017: [Errno -2] Name or service not known",
    "connection_target": {
      "host": "mongodb-invalid",
      "port": 27017,
      "database": "testdb",
      "user": "None"
    },
    "actionable_hint": "Verifica che MongoDB sia attivo e raggiungibile all'host 'mongodb-invalid' sulla porta 27017. In Kubernetes, controlla il nome del Service K8s."
  }
}
```

---

### Caso C: Collezione Inesistente (404 con Elenco Collezioni)

**Richiesta**:
```bash
curl -i -X GET "http://[HOST]/collections/collezione_inesistente/metadata"
```
**Risposta HTTP (404)**:
```json
{
  "detail": {
    "error_category": "COLLECTION_NOT_FOUND",
    "summary": "La collezione 'collezione_inesistente' non esiste nel database 'testdb'",
    "requested_collection": "collezione_inesistente",
    "database": "testdb",
    "available_collections": [
      "cittadini",
      "servizi_pubblici",
      "pratiche_amministrative",
      "metriche_accessi",
      "vista_cittadini_per_comune"
    ],
    "actionable_hint": "Verifica il nome della collezione specificato nell'URL."
  }
}
```

---

## 5. Il Nuovo Endpoint `/health`

L'endpoint `/health` è stato potenziato per fungere da **strumento di diagnostica istantaneo**:

### In caso di connessione OK:
```bash
curl -X GET "http://[HOST]/health"
```
```json
{
  "status": "healthy",
  "mongodb": "connected",
  "database": "testdb",
  "host": "mongodb",
  "port": 27017,
  "auth_configured": true,
  "latency_ms": 0.58,
  "version": "1.0.0",
  "timestamp": "2026-09-05T13:16:30.283171+00:00"
}
```

### In caso di connessione KO:
```json
{
  "status": "unhealthy",
  "mongodb": "disconnected",
  "database": "testdb",
  "host": "mongodb",
  "port": 27017,
  "auth_configured": true,
  "latency_ms": 3001.30,
  "version": "1.0.0",
  "timestamp": "2026-09-05T13:15:24.398996+00:00",
  "diagnostic_error": {
    "error_category": "MONGODB_AUTHENTICATION_FAILED",
    "summary": "Autenticazione MongoDB fallita...",
    "actionable_hint": "Verifica 'MONGO_USER' e 'MONGO_PASSWORD' nei Secret Kubernetes."
  }
}
```

---

## 6. Istruzioni per il Deploy dell'Immagine Docker v1.0.1

### Opzione A: Caricamento da Archivio `.tar`
Per gli ambienti senza accesso diretto a internet, l'immagine è esportata nel file `mongo-fastapi-v1.0.1.tar` (64 MB):

```bash
# 1. Caricare l'immagine nel demone Docker del cluster/nodo
docker load -i mongo-fastapi-v1.0.1.tar

# 2. Tag e Push sul registry aziendale privato (es. Harbor / Nexus)
docker tag mongo-fastapi:v1.0.1 registry.dss.regione.puglia.it/dss/mongo-fastapi:v1.0.1
docker push registry.dss.regione.puglia.it/dss/mongo-fastapi:v1.0.1

# 3. Aggiornamento Deployment Kubernetes
kubectl set image deployment/fastapi-mongodb-api fastapi=registry.dss.regione.puglia.it/dss/mongo-fastapi:v1.0.1 -n metadata
```

### Opzione B: Build Diretta da Repository Git
```bash
git clone https://github.com/dataappengineer/mongo-fastAPI.git
cd mongo-fastAPI
docker build -t mongo-fastapi:v1.0.1 -f deployment/docker/Dockerfile.prod .
```
