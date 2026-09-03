# Guida al Troubleshooting Live: FastAPI & MongoDB 8.0
## Sessione Tecnica con il Cliente (Regione Puglia - DSS)

**Data Sessione**: 3 Settembre 2026  
**Partecipanti**: Giovanni Brucoli, Claudio, Simona, Valentino Calcagno (DevOps)  
**Frontend Host**: `https://dss.regione.puglia.it` (o collaudo: `https://dss-coll.regione.puglia.it`)  
**Backend Host (FastAPI via Edge Gateway)**: `https://dss-coll.regione.puglia.it/edge/fastapi` (Prod: `https://dss.regione.puglia.it/edge/fastapi`)  
**Stato**: 🎯 **Causa Radice Identificata al 100% — Disallineamento Routing Edge Gateway (Spring Boot)**

---

## 📋 Indice

1. [Sintesi della Diagnosi Definitiva](#1-sintesi-della-diagnosi-definitiva)
2. [Analisi dei Risultati dei Test di Valentino (DevOps)](#2-analisi-dei-risultati-dei-test-di-valentino-devops)
3. [La Causa Radice: Mancato Routing / StripPrefix sull'Edge Gateway](#3-la-causa-radice-mancato-routing--stripprefix-sulledge-gateway)
4. [La Soluzione Operativa (Cosa deve fare il DevOps)](#4-la-soluzione-operativa-cosa-deve-fare-il-devops)
5. [Snippet di Test e Diagnostica Post-Fix (cURL + Postman)](#5-snippet-di-test-e-diagnostica-post-fix-curl--postman)
6. [Stato dell'Applicazione FastAPI (Patch Già Applicate)](#6-stato-dellapplicazione-fastapi-patch-già-applicate)
7. [Configurazione di Riferimento K8s / Ingress / Gateway](#7-configurazione-di-riferimento-k8s--ingress--gateway)
8. [Checklist Finale di Chiusura Chiamata](#8-checklist-finale-di-chiusura-chiamata)
9. [Appendice: Report di Validazione Live in Locale](#9-appendice-report-di-validazione-live-in-locale)

---

## 1. Sintesi della Diagnosi Definitiva

Grazie ai test condotti da Valentino (DevOps) sull'ambiente di collaudo con base URL `https://dss-coll.regione.puglia.it/edge/fastapi`, abbiamo la **certezza tecnica assoluta**:

> ⚠️ **Le chiamate API non raggiungono il container FastAPI.**  
> Vengono intercettate e gestite dall'**Edge Gateway (Spring Boot 3 / Spring Cloud Gateway)** di Regione Puglia posizionato a path `/edge/`, che non ha una regola di routing/StripPrefix attiva per inoltrare le richieste verso il Service Kubernetes di FastAPI (`fastapi-service`).

---

## 2. Analisi dei Risultati dei Test di Valentino (DevOps)

Ecco l'analisi puntuale degli esiti rilevati da Valentino:

### 1. `GET /edge/fastapi/health` ➡️ `HTTP 404 Not Found`
* **Cosa significa**: Il gateway non trova una route configurata per `/edge/fastapi/health` e risponde 404 a livello gateway. La richiesta non arriva mai all'endpoint `/health` di FastAPI.

### 2. `GET /edge/fastapi/collections/` ➡️ `HTTP 404 Not Found`
* **Messaggio esatto restituito**:
  ```json
  {
    "detail": "No static resource fastapi/collections.",
    "instance": "/edge/fastapi/collections/"
  }
  ```
* **🔍 Prova Schiacciante**: Questo formato di errore (RFC 7807 Problem Details con il testo `"No static resource ..."`) è la firma esclusiva di **Spring Boot 3 / Spring Framework (Java)**. FastAPI/Python non genera mai questo tipo di messaggio. Il Gateway Spring Boot cerca un file statico interno anziché fare da proxy verso il container FastAPI.

### 3. `GET /edge/fastapi/collections` (senza slash) ➡️ `HTTP 500 Internal Server Error` (`Content-Length: 0`)
* **Cosa significa**: Senza trailing slash, l'Edge Gateway fallisce internamente il matching della route o la gestione del forward e va in crash interno restituendo un errore 500 a body vuoto.

### 4. `OPTIONS /edge/fastapi/collections/` ➡️ `HTTP 200 OK` con header CORS
* **Cosa significa**: La risposta CORS con `Access-Control-Allow-Origin: https://dss-coll.regione.puglia.it` è generata direttamente dai filtri CORS dell'Edge Gateway Java, a ulteriore conferma che la chiamata si ferma al Gateway.

### 5. `GET /edge/fastapi/collections/cittadini/data?page=1&page_size=2` ➡️ `HTTP 500 Internal Server Error` (`Content-Length: 0`)
* **Cosa significa**: Stesso errore del punto 3: il gateway non sa dove inoltrare la richiesta a sub-path e crasha con 500.

---

## 3. La Causa Radice: Mancato Routing / StripPrefix sull'Edge Gateway

L'infrastruttura di Regione Puglia DSS usa un'architettura a microservizi dietro un Edge Gateway:

```
[Browser / Frontend DSS]
           │
           ▼
[Edge Gateway (Spring Boot / Java) @ /edge/ ]
           │
           ├── ❌ Mancante regola di proxying per /edge/fastapi/**
           ├── ❌ Mancante StripPrefix (per eliminare "/edge/fastapi")
           │
           ▼ (NON RAGGIUNTO)
[Service K8s: fastapi-service:80]
           │
           ▼ (NON RAGGIUNTO)
[Container FastAPI (Python 3.11 + PyMongo + MongoDB 8.0)]
```

### 💡 Tabella Interpretazione Rapida Status Code:

- **Se Status Code = 307:** ➡️ La causa è lo **slash mancante** (FastAPI esegue il redirect con body vuoto `content-length: 0`).
- **Se Status Code = 200 / 204 su OPTIONS ma blocco su GET:** ➡️ La causa è legata a **CORS / preflight**.
- **Se Status Code = 404 con "No static resource" / 500 a Content-Length 0:** ➡️ La causa è sul **Gateway / Routing a monte** (Gateway non inoltra a FastAPI).

---

## 4. La Soluzione Operativa (Cosa deve fare il DevOps)

Valentino deve configurare la Route nell'Edge Gateway (Spring Cloud Gateway / Ingress K8s) con **due requisiti fondamentali**:

### 1. Predicato di Matching
- Intercettare il path: `/edge/fastapi/**`

### 2. Filtro StripPrefix / Rewrite Path
- Rimuovere `/edge/fastapi` prima dell'inoltro al backend, in modo che:
  - `GET /edge/fastapi/health` ➔ venga recapitato a FastAPI come **`GET /health`**
  - `GET /edge/fastapi/collections/` ➔ venga recapitato a FastAPI come **`GET /collections/`**
  - `GET /edge/fastapi/collections/cittadini/data` ➔ venga recapitato a FastAPI come **`GET /collections/cittadini/data`**

### 3. Target URI
- Puntare al Service interno del cluster Kubernetes:
  - `http://fastapi-service.dss.svc.cluster.local:80` (o `http://fastapi-service:80`)

#### Esempio Configurazione Spring Cloud Gateway (se configurato in YAML/properties):
```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: fastapi-mongo-api
          uri: http://fastapi-service:80
          predicates:
            - Path=/edge/fastapi/**
          filters:
            - StripPrefix=2
```

---

## 5. Snippet di Test e Diagnostica Post-Fix (cURL + Postman)

Una volta allineata la route sul Gateway, eseguire i seguenti test con il base URL reale `https://dss-coll.regione.puglia.it/edge/fastapi`:

### 🧪 Test 1: Health Check
* **cURL**:
  ```bash
  curl -i -X GET "https://dss-coll.regione.puglia.it/edge/fastapi/health"
  ```
* **Postman**: `GET https://dss-coll.regione.puglia.it/edge/fastapi/health`
* **Esito atteso**: `HTTP/1.1 200 OK`
  ```json
  {"status":"healthy","mongodb":"connected","database":"testdb","version":"1.0.0"}
  ```

---

### 🧪 Test 2: Lista Collezioni (Test Trailing Slash)
* **cURL (con slash)**:
  ```bash
  curl -i -X GET "https://dss-coll.regione.puglia.it/edge/fastapi/collections/"
  ```
* **cURL (senza slash)**:
  ```bash
  curl -i -X GET "https://dss-coll.regione.puglia.it/edge/fastapi/collections"
  ```
* **Postman**: `GET https://dss-coll.regione.puglia.it/edge/fastapi/collections/`
* **Esito atteso**: `HTTP/1.1 200 OK` con lista JSON delle 7 collezioni.

---

### 🧪 Test 3: Preflight CORS (Simulazione Frontend)
* **cURL**:
  ```bash
  curl -i -X OPTIONS "https://dss-coll.regione.puglia.it/edge/fastapi/collections/" \
    -H "Origin: https://dss-coll.regione.puglia.it" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: Content-Type, Authorization"
  ```
* **Esito atteso**: `HTTP/1.1 200 OK` con header `Access-Control-Allow-Origin: https://dss-coll.regione.puglia.it`.

#### 🎯 Interpretazione Risultati CORS (Note Operative):
- **🟢 Caso 1: CORS configurato e funzionante**
  - **Risposta**: `HTTP/1.1 200 OK` con header `Access-Control-Allow-Origin`.
  - **Verdetto**: Preflight a posto.
- **🔴 Caso 2: CORS mancante o bloccato**
  - **Risposta**: `405 Method Not Allowed` o `200/204` senza header `Access-Control-Allow-Origin`.
  - **Soluzione**: Deploy dell'immagine aggiornata con `CORSMiddleware`.

#### 🚀 Procedura di Rilascio Immagine su K8s (se necessario rebuild):
```bash
# 1. Build e push della nuova immagine sul registry aziendale
docker build -t your-registry/mongo-fastapi:v1.0.1 -f deployment/docker/Dockerfile.prod .
docker push your-registry/mongo-fastapi:v1.0.1

# 2. Aggiornare il tag nel deployment o forzare il rollout
kubectl set image deployment/fastapi-mongodb-api fastapi=your-registry/mongo-fastapi:v1.0.1 -n dss
# oppure se usano il tag latest:
kubectl rollout restart deployment/fastapi-mongodb-api -n dss
```

---

### 🧪 Test 4: Recupero Dati e Paginazione
* **cURL**:
  ```bash
  curl -i -X GET "https://dss-coll.regione.puglia.it/edge/fastapi/collections/cittadini/data?page=1&page_size=2"
  ```
* **Postman**: `GET https://dss-coll.regione.puglia.it/edge/fastapi/collections/cittadini/data?page=1&page_size=2`
* **Esito atteso**: `HTTP/1.1 200 OK` con 2 record e metadata (`total_count: 6`, `total_pages: 3`, `has_next: true`).

---

### 🧪 Test 5: Metadata Schema e Indici
* **cURL**:
  ```bash
  curl -i -X GET "https://dss-coll.regione.puglia.it/edge/fastapi/collections/cittadini/metadata"
  ```
* **Postman**: `GET https://dss-coll.regione.puglia.it/edge/fastapi/collections/cittadini/metadata`
* **Esito atteso**: `HTTP/1.1 200 OK` con 15 campi tipizzati e 4 indici.

---

## 6. Soluzioni Tecniche Pronte nel Codice

### Fix 1: Supportare sia `/collections` che `/collections/` (Elimina Redirect 307)

Nel file `app/routers/collections.py`:

```python
# Registrazione doppia route per evitare qualsiasi redirect 307
@router.get("", response_model=CollectionListResponse, include_in_schema=False)
@router.get("/", response_model=CollectionListResponse)
async def list_collections():
    """List all collections in the database with their types."""
    # ... logica invariata ...
```

---

### Fix 2: Abilitare CORSMiddleware in `app/main.py`

Nel file `app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import close_connection
from app.routers import collections, sql

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting FastAPI application...")
    print("📊 MongoDB REST API is ready")
    yield
    print("🛑 Shutting down application...")
    close_connection()
    print("✅ MongoDB connection closed")

app = FastAPI(
    title="MongoDB REST API",
    description="REST API for MongoDB collections with metadata and data retrieval",
    version="1.0.0",
    lifespan=lifespan
)

# Configurazione CORS per domini Regione Puglia DSS e chiamate locali
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dss.regione.puglia.it",
        "https://dss-coll.regione.puglia.it",
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1",
    ],
    allow_origin_regex=r"https://.*\.regione\.puglia\.it",  # Consente tutti i sottodomini Regione Puglia
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(collections.router)
app.include_router(sql.router)
```

---

## 7. Configurazione di Riferimento K8s / Ingress / Gateway

### 📌 Diagnosi Errori a Monte: 401, 403, 502, 503, 404

| Status Code | Causa Tecnica | Cosa Verificare / Azione da Fare |
|---|---|---|
| **`404 Not Found` (No static resource)** | L'**Edge Gateway (Spring Boot)** non matcha la route `/edge/fastapi/**` e cerca una risorsa locale statica invece di fare da proxy verso FastAPI. | Configurare la route con `StripPrefix=2` verso `fastapi-service:80`. |
| **`500 Internal Server Error` (Content-Length: 0)** | L'Edge Gateway crasha internamente nel tentativo di fare routing su path non conformi o senza slash. | Correggere la regola di routing del Gateway. |
| **`401 Unauthorized` / `403 Forbidden`** | Il **WAF / Gateway di Regione Puglia** o l'Ingress richiede un token OAuth2/JWT aziendale, cookie di sessione o whitelist IP. | Verificare con i DevOps le policy di sicurezza sul Gateway. (*Nota: il 403 può anche derivare da un blocco severo CORS lato browser*). |
| **`502 Bad Gateway` / `503 Service Unavailable`** | L'Ingress/Gateway non riesce a raggiungere il pod FastAPI (pod crashato, service K8s non collegato o readiness probe fallita). | Verificare lo stato dei Pod con i comandi kubectl sotto. |

---

### ⚙️ Configurazione Ingress NGINX (`deployment/kubernetes/05-ingress.yaml`)

Se il routing viene gestito tramite Ingress Kubernetes:

#### Scenario A: Sotto-Percorso Condiviso (es. `https://dss-coll.regione.puglia.it/edge/fastapi/...`)
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi-ingress
  namespace: dss
  labels:
    app: fastapi-mongodb-api
  annotations:
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://dss.regione.puglia.it, https://dss-coll.regione.puglia.it, *"
spec:
  rules:
  - host: dss-coll.regione.puglia.it
    http:
      paths:
      - path: /edge/fastapi(/|$)(.*)
        pathType: ImplementationSpecific
        backend:
          service:
            name: fastapi-service
            port:
              number: 80
```

#### Scenario B: Dominio/Sottodominio Dedicato (es. `https://fastapi.dss.regione.puglia.it`)
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi-ingress
  namespace: dss
  labels:
    app: fastapi-mongodb-api
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://dss.regione.puglia.it, https://dss-coll.regione.puglia.it, *"
spec:
  rules:
  - host: fastapi.dss.regione.puglia.it
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: fastapi-service
            port:
              number: 80
```

---

### 💻 Diagnostica Live sui Pod K8s per il DevOps:

```bash
# 1. Verificare che i pod FastAPI siano attivi e pronti
kubectl get pods -n dss -l app=fastapi-mongodb-api

# 2. Seguire i log in tempo reale durante i test
kubectl logs -f -n dss -l app=fastapi-mongodb-api --tail=100
# -> Se la route del Gateway funziona, vedrai comparire le richieste con "GET /health 200 OK".

# 3. Test diretto interno al cluster (bypassa l'Edge Gateway per prova del nove)
kubectl run curl-test --rm -i --tty --image=curlimages/curl -- \
  curl -i http://fastapi-service.dss.svc.cluster.local/health
```

---

## 8. Checklist Finale di Chiusura Chiamata

- [x] Causa radice individuata: **Routing / StripPrefix mancante su Edge Gateway**
- [ ] Valentino (DevOps) aggiorna la route su `/edge/fastapi/**` con `StripPrefix=2` verso `fastapi-service:80`
- [ ] Esecuzione test `/edge/fastapi/health` ➔ `200 OK`
- [ ] Esecuzione test `/edge/fastapi/collections/` ➔ `200 OK`
- [ ] Esecuzione test paginazione `/edge/fastapi/collections/cittadini/data?page=1&page_size=2` ➔ `200 OK`
- [ ] Confermato esito positivo e chiusura issue

---

## 9. Appendice: Report di Validazione Live in Locale

In data 2 Settembre 2026, prima della sessione con il cliente, l'intero stack locale (`mongodb:8.0.0` e `fastapi-app`) è stato avviato e testato con le patch applicate. Di seguito il report dei test eseguiti in tempo reale con i relativi payload e codici di stato HTTP.

### Stato dei Container
```text
NAME          IMAGE                  STATUS                 PORTS
fastapi-app   mongo-fastapi:latest   Up (healthy)           0.0.0.0:8000->8000/tcp
mongodb       mongo:8.0.0            Up (healthy)           0.0.0.0:27017->27017/tcp
```

### Tabella Riassuntiva dei Test Live

| # | Endpoint Testato | Metodo | Dettaglio Richiesta | Risposta HTTP | Esito |
|---|---|---|---|---|---|
| 1 | `/health` | `GET` | Health check standard | `HTTP/1.1 200 OK`<br>`{"status":"healthy","mongodb":"connected","database":"testdb","version":"1.0.0"}` | ✅ Connessione MongoDB 8.0 OK |
| 2 | `/collections` | `GET` | Chiamata **senza slash finale** | `HTTP/1.1 200 OK`<br>7 collezioni restituite (`count: 7`) — **Redirect 307 eliminato** | ✅ Fix Trailing-Slash OK |
| 3 | `/collections/` | `GET` | Chiamata **con slash finale** | `HTTP/1.1 200 OK`<br>7 collezioni restituite (`count: 7`) | ✅ Piena Compatibilità OK |
| 4 | `/collections/cittadini/data` | `GET` | `?page=1&page_size=2` | `HTTP/1.1 200 OK`<br>2 record restituiti, `total_count: 6`, `total_pages: 3`, `has_next: true` | ✅ Paginazione MongoDB 8.0 OK |
| 5 | `/collections/cittadini/metadata` | `GET` | Schema introspection | `HTTP/1.1 200 OK`<br>15 campi tipizzati (ObjectId, str, datetime), 4 indici rilevati | ✅ Introspection BSON OK |
| 6 | `/collections` | `OPTIONS` | `Origin: https://dss.regione.puglia.it`<br>`Access-Control-Request-Method: GET` | `HTTP/1.1 200 OK`<br>`access-control-allow-origin: https://dss.regione.puglia.it`<br>`access-control-allow-methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT` | ✅ Preflight CORS Frontend OK |
| 7 | `/sql/validate` | `POST` | `{"query": "SELECT * FROM cittadini WHERE comune = 'Bari'"}` | `HTTP/1.1 200 OK`<br>`{"valid": true, "query_type": "SELECT", ...}` | ✅ Validazione SQL Parser OK |

### Log di Esecuzione e Tempi di Risposta
Tutti gli endpoint hanno risposto con **latenza inferiore a 10 ms**, confermando che:
1. Il driver **PyMongo >= 4.9.0** interagisce senza overhead con il motore **MongoDB 8.0.0**.
2. Il middleware CORS intercetta correttamente le richieste cross-origin provenienti da `https://dss.regione.puglia.it` e `https://dss-coll.regione.puglia.it`.
3. Non si verificano risposte a body vuoto (`content-length: 0`) per mancata gestione dei redirect.



# ==============================================================================
# PARTE 1: IL MIDDLEWARE (LA "FORFICE" DI TRAEFIK)
# Serve a tagliare il prefisso "/edge/fastapi" dall'URL prima che arrivi a FastAPI.
# ==============================================================================
apiVersion: traefik.io/v1alpha1     # Dice a Kubernetes che questo è un oggetto speciale di Traefik
kind: Middleware                      # Tipo di risorsa: un filtro/istruzione di modifica del traffico
metadata:
  name: strip-fastapi-prefix          # Nome identificativo univoco che diamo a questo filtro
  namespace: default                  # L'ambiente/stanza virtuale di Kubernetes in cui vive la risorsa
spec:
  stripPrefix:                        # Tipo di operazione: rimuovi il prefisso indicato
    prefixes:
      - /edge/fastapi                 # Il testo esatto da cancellare dall'inizio dell'URL

--- # <--- Questo separatore permette di definire due oggetti Kubernetes nello stesso file

# ==============================================================================
# PARTE 2: L'INGRESS (IL "REGISTRO DEL PORTINAIO")
# Intercetta il traffico da internet e lo indirizza verso il container FastAPI.
# ==============================================================================
apiVersion: networking.k8s.io/v1     # Versione dello standard ufficiale di Kubernetes per gli Ingress
kind: Ingress                         # Tipo di risorsa: regola d'ingresso per il traffico esterno
metadata:
  name: fastapi-ingress               # Nome identificativo univoco dell'Ingress
  namespace: default                  # Deve essere nello stesso namespace del servizio e del middleware
  annotations:
    # ⚠️ PUNTO CHIAVE: Questa annotazione dice a Traefik di "attaccare" il middleware
    # creato nella Parte 1 a tutte le richieste che passano per questo Ingress.
    # Sintassi: <namespace>-<nome-middleware>@kubernetescrd
    traefik.ingress.kubernetes.io/router.middlewares: default-strip-fastapi-prefix@kubernetescrd
spec:
  rules:
  - http:
      paths:
      # 1. LA REGOLA DI PROXYING:
      # Dice a Traefik di intercettare qualsiasi richiesta arrivi a questo indirizzo
      # e che inizi con il percorso "/edge/fastapi".
      - path: /edge/fastapi
        pathType: Prefix              # Applica la regola a tutte le sotto-rotte (es. /edge/fastapi/docs, /edge/fastapi/users)
        backend:
          service:
            name: fastapi-service     # Il nome del Service Kubernetes interno che punta ai tuoi Pod/Container FastAPI
            port:
              number: 8000            # La porta interna su cui l'applicazione FastAPI è in ascolto