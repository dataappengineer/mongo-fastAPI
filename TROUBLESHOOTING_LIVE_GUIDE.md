# Guida al Troubleshooting Live: FastAPI & MongoDB 8.0
## Sessione Tecnica con il Cliente (Regione Puglia - DSS)

**Data Sessione**: 2 Settembre 2026  
**Partecipanti**: Giovanni Brucoli, Claudio, Simona  
**Target Host**: `https://dss.regione.puglia.it` (o ambiente coll: `https://dss-coll.regione.puglia.it`)  
**Stato**: 🛠️ Guida Operativa & Runbook di Diagnosi

---

## 📋 Indice

1. [Sintesi del Problema Riscontrato](#1-sintesi-del-problema-riscontrato)
2. [Analisi degli Header Ricevuti dal Cliente](#2-analisi-degli-header-ricevuti-dal-cliente)
3. [Le 3 Cause Principali Identificate](#3-le-3-cause-principali-identificate)
4. [Copione della Chiamata Live (Step-by-Step)](#4-copione-della-chiamata-live-step-by-step)
5. [Snippet di Test e Diagnostica (Comandi cURL)](#5-snippet-di-test-e-diagnostica-comandi-curl)
6. [Soluzioni Tecniche Pronte nel Codice](#6-soluzioni-tecniche-pronte-nel-codice)
7. [Verifica e Fix del Deployment Kubernetes (K8s)](#7-verifica-e-fix-del-deployment-kubernetes-k8s)
8. [Checklist Finale di Chiusura Chiamata](#8-checklist-finale-di-chiusura-chiamata)

---

## 1. Sintesi del Problema Riscontrato

Il cliente ha effettuato test sulle chiamate API dopo l'aggiornamento a **MongoDB 8.0 / PyMongo** e ha ricevuto una risposta con payload vuoto (`content-length: 0`) accompagnata da header di sicurezza del Reverse Proxy/Gateway aziendale di Regione Puglia (`dss.regione.puglia.it` / `dss-coll.regione.puglia.it`).

---

## 2. Analisi degli Header Ricevuti dal Cliente

Analizziamo voce per voce la risposta inviata dal cliente:

| Header | Valore | Significato Diagnostico |
|---|---|---|
| `content-length` | `0` | Il corpo della risposta HTTP è **completamente vuoto** (0 byte). |
| `content-security-policy` | `... connect-src 'self' https://dss-coll... https://dss...` | La richiesta transita tramite il Gateway/WAF di Regione Puglia (DSS). |
| `vary` | `Origin, Access-Control-Request-Method, Access-Control-Request-Headers` | La richiesta è stata valutata come cross-origin (CORS) o preflight da un browser/client. |
| `cache-control` | `no-cache, no-store, max-age=0, must-revalidate` | Risposta non cachata (tipico di redirect, preflight o chiamate API). |
| `x-frame-options`, `strict-transport-security` | Standard DSS | Header di sicurezza iniettati dall'Ingress/Reverse Proxy DSS. |

---

## 3. Le 3 Cause Principali Identificate

### Causa A: Trailing Slash Redirect (Status `307 Temporary Redirect`)
- In FastAPI, l'endpoint `@router.get("/")` sotto il prefisso `/collections` risponde a `/collections/`.
- Se il client chiama `GET /collections` (senza slash finale), FastAPI risponde con **`307 Temporary Redirect`** verso `/collections/` con body vuoto (`content-length: 0`).
- Se il client HTTP, Postman, il browser o il gateway non segue automaticamente il redirect, l'utente vede una risposta vuota a 0 byte.

### Causa B: Richiesta Preflight CORS (`OPTIONS`) non gestita
- Se la chiamata parte da una web application su `dss.regione.puglia.it` o `dss-coll.regione.puglia.it`, il browser invia prima una richiesta HTTP `OPTIONS`.
- Se `CORSMiddleware` non è configurato in FastAPI, l'applicazione risponde con `405 Method Not Allowed`, bloccando il payload.

### Causa C: Regola `rewrite-target` errata nell'Ingress Kubernetes
- Nel manifest Ingress K8s, l'annotazione `nginx.ingress.kubernetes.io/rewrite-target: /` senza cattura regex riscrittiva (`/(.*)` -> `/$1`) può riscrivere qualsiasi URI (es. `/collections/cittadini/data`) a `/`, servendo l'endpoint root anziché l'API richiesta.

---

## 4. Copione della Chiamata Live (Step-by-Step)

Durante la chiamata con Claudio e Simona, seguire questa scaletta:

### 🔹 Minuto 0-5: Accoglienza e Chiarimento Dati
1. Ringraziare per il riscontro e condividere lo schermo.
2. Chiedere a Claudio/Simona:
   - *"Qual è l'URL esatto che stavate chiamando?"* (es. `/health`, `/collections`, `/collections/cittadini/data`)
   - *"Qual è il metodo HTTP usato?"* (GET, POST, etc.)
   - *"Lo state chiamando da browser, Postman o curl?"*
   - *"Qual è lo Status Code numerico?"* (200, 307, 404, 405, 502)

### 🔹 Minuto 5-15: Esecuzione Test Live Guidati
Eseguire insieme a loro i comandi cURL diagnostici (mostrati nella Sezione 5):
1. Test `/health` (verifica connettività base e MongoDB 8).
2. Test `/collections` vs `/collections/` (con `-i` per vedere lo status code 307 vs 200).
3. Test `-L` (follow redirect).
4. Test paginazione `/collections/cittadini/data?page=1&page_size=2`.

### 🔹 Minuto 15-25: Applicazione dei Fix
1. Mostrare il supporto doppio per trailing slash (`/collections` e `/collections/` senza redirect 307).
2. Mostrare l'abilitazione di `CORSMiddleware` in FastAPI.
3. Rilasciare/applicare la patch.

### 🔹 Minuto 25-30: Validazione Finale e Chiusura
1. Ripetere la chiamata del cliente: deve restituire `HTTP 200 OK` con il payload JSON.
2. Confermare che MongoDB 8 risponde correttamente su tutti gli endpoint.

---

## 5. Snippet di Test e Diagnostica (Comandi cURL)

### Test 1: Health Check (Verifica Base)
```bash
# Sostituire con l'host corretto (es. https://dss.regione.puglia.it)
curl -i -X GET "https://dss.regione.puglia.it/health"
```
**Output atteso**:
```http
HTTP/1.1 200 OK
content-type: application/json

{"status":"healthy","mongodb":"connected","database":"testdb","version":"1.0.0"}
```

---

### Test 2: Verifica Trailing Slash (Senza Redirect)
```bash
# Chiamata CON slash finale:
curl -i -X GET "https://dss.regione.puglia.it/collections/"

# Chiamata SENZA slash finale (per verificare se restituisce 307):
curl -i -X GET "https://dss.regione.puglia.it/collections"

# Chiamata con Follow Redirect (-L):
curl -i -L -X GET "https://dss.regione.puglia.it/collections"
```

---

### Test 3: Verifica Preflight CORS (Simulazione Browser)
```bash
curl -i -X OPTIONS "https://dss.regione.puglia.it/collections/" \
  -H "Origin: https://dss.regione.puglia.it" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type, Authorization"
```
**Output atteso con CORS attivo**:
```http
HTTP/1.1 200 OK
access-control-allow-origin: https://dss.regione.puglia.it
access-control-allow-methods: GET, POST, PUT, DELETE, OPTIONS
access-control-allow-headers: Content-Type, Authorization
```

---

### Test 4: Recupero Dati e Paginazione
```bash
curl -i -L -X GET "https://dss.regione.puglia.it/collections/cittadini/data?page=1&page_size=2"
```

---

### Test 5: Metadata Schema e Indici
```bash
curl -i -L -X GET "https://dss.regione.puglia.it/collections/cittadini/metadata"
```

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
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(collections.router)
app.include_router(sql.router)
```

---

## 7. Verifica e Fix del Deployment Kubernetes (K8s)

### Controllo `deployment/kubernetes/05-ingress.yaml`

Attenzione alla configurazione del rewrite target dell'Ingress NGINX:

#### Configurazione Corretta (Senza subpath rewrite distruttivo):
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi-ingress
  namespace: dss
  labels:
    app: fastapi-mongodb-api
  annotations:
    # Se il servizio è esposto sulla root dell'host (fastapi.dss.regione.puglia.it):
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://dss.regione.puglia.it, https://dss-coll.regione.puglia.it"
    nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, DELETE, OPTIONS"
    nginx.ingress.kubernetes.io/cors-allow-headers: "DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Authorization"
spec:
  rules:
  - host: dss.regione.puglia.it
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

#### Se invece è esposto su un sotto-percorso (es. `/api/mongo/(.*)`):
```yaml
  annotations:
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  rules:
  - host: dss.regione.puglia.it
    http:
      paths:
      - path: /api/mongo(/|$)(.*)
        pathType: ImplementationSpecific
        backend:
          service:
            name: fastapi-service
            port:
              number: 80
```

---

### Diagnostica Live sui Pod K8s (se hanno accesso al cluster)

```bash
# 1. Verificare lo stato dei pod
kubectl get pods -n dss -l app=fastapi-mongodb-api

# 2. Leggere i log in tempo reale per vedere le chiamate HTTP in arrivo
kubectl logs -f -n dss -l app=fastapi-mongodb-api --tail=100

# 3. Testare l'endpoint direttamente all'interno del cluster
kubectl run curl-test --rm -i --tty --image=curlimages/curl -- \
  curl -i http://fastapi-service.dss.svc.cluster.local/health
```

---

## 8. Checklist Finale di Chiusura Chiamata

- [ ] Identificato l'URL esatto chiamato dal client
- [ ] Verificato lo Status Code HTTP ricevuto
- [ ] Testato `/health` (confermato `mongodb: connected`, versione 8.0)
- [ ] Eliminato il redirect 307 sul trailing slash (`/collections` e `/collections/`)
- [ ] Abilitato `CORSMiddleware` in FastAPI per richieste da browser
- [ ] Allineato l'Ingress Kubernetes (se routing su subpath)
- [ ] Eseguito smoke test congiunto con Claudio e Simona
- [ ] Confermato esito positivo e chiusura issue
