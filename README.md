# API REST MongoDB - Regione Puglia

API REST sviluppata con FastAPI e PyMongo per interagire con database MongoDB. Fornisce endpoint per gestire collezioni, metadati, dati e validazione di query SQL per PostgreSQL.

## 🎯 Caratteristiche Principali

✅ **Gestione Collezioni MongoDB:**
- Elenco di tutte le collezioni con rilevamento automatico del tipo (collection, view, timeseries, capped)
- Metadati dettagliati (campi, tipi di dati, conteggio documenti, indici)
- Estrazione dati con limite righe configurabile (`max_righe`)

✅ **Validazione Query SQL:**
- Validazione sintattica per query PostgreSQL
- Rilevamento errori comuni e pattern SQL injection
- Formattazione automatica delle query

✅ **Plug & Play:**
- Funziona con MongoDB in Docker (`mongo:7.0.14`) o deployment esterni
- Configurazione tramite variabili d'ambiente

✅ **Docker Ready:**
- Setup completo con Docker Compose
- Hot-reload per sviluppo rapido
- Script di seeding per dati di test

## 📁 Struttura Progetto

```
mongo-fastAPI/
├── app/
│   ├── __init__.py
│   ├── main.py              # Applicazione FastAPI
│   ├── database.py          # Connessione MongoDB
│   ├── models.py            # Modelli Pydantic
│   └── routers/
│       ├── __init__.py
│       ├── collections.py   # Endpoint collezioni MongoDB
│       └── sql.py           # Endpoint validazione SQL
├── scripts/
│   └── seed_mongo.py        # Script popolamento database
├── docker-compose.yml       # Configurazione Docker Compose
├── Dockerfile               # Container FastAPI
├── requirements.txt         # Dipendenze Python
├── .env                     # Variabili d'ambiente
└── README.md
```

## 🚀 Avvio Rapido con Docker

### Prerequisiti
- Docker e Docker Compose installati sul sistema
- Porte 8000 e 27017 disponibili

### 1. Costruire l'immagine Docker

```bash
docker build -t mongo-fastapi:latest .
```

### 2. Avviare i servizi

```bash
docker-compose up -d
```

Questo avvierà:
- **MongoDB** sulla porta 27017 (immagine: `mongo:7.0.14`)
- **API FastAPI** sulla porta 8000

### 3. Popolare il database con dati di test (opzionale)

```bash
docker-compose exec fastapi python scripts/seed_mongo.py
```

Questo crea:
- 3 collezioni standard: `cittadini`, `servizi_pubblici`, `pratiche_amministrative`
- 2 view: `vista_cittadini_per_comune`, `vista_servizi_per_categoria`
- 1 collezione timeseries: `metriche_accessi`
- 1 collezione capped: `log_eventi` (può essere creata manualmente)

### 4. Accedere all'API

- **URL Base API:** http://localhost:8000
- **Documentazione Interattiva (Swagger):** http://localhost:8000/docs
- **Documentazione ReDoc:** http://localhost:8000/redoc
- **Schema OpenAPI:** http://localhost:8000/openapi.json

## 📚 Documentazione API

### Endpoint 1: Elenco Collezioni

**Descrizione:** Restituisce l'elenco di tutte le collezioni presenti nel database con il loro tipo (collection, view, timeseries, capped).

**Endpoint:**
```
GET /collections/
```

**Risposta:**
```json
{
  "collections": [
    {
      "name": "cittadini",
      "type": "collection"
    },
    {
      "name": "vista_cittadini_per_comune",
      "type": "view"
    },
    {
      "name": "metriche_accessi",
      "type": "timeseries"
    },
    {
      "name": "log_eventi",
      "type": "capped"
    }
  ],
  "count": 4
}
```

**Tipi di Collezione Supportati:**
- `collection`: Collezione standard MongoDB
- `view`: Vista di sola lettura basata su aggregation pipeline
- `timeseries`: Collezione ottimizzata per dati con timestamp
- `capped`: Collezione a dimensione fissa con comportamento FIFO

**Esempio di utilizzo:**
```bash
curl http://localhost:8000/collections/
```

---

### Endpoint 2: Metadati Collezione

**Descrizione:** Restituisce i metadati dettagliati di una collezione specifica, inclusi tipi di dati dei campi, esempi di valori, conteggio documenti, dimensione e indici.

**Endpoint:**
```
GET /collections/{nome_collezione}/metadata
```

**Parametri:**
- `nome_collezione` (path): Nome della collezione da analizzare

**Risposta:**
```json
{
  "collection_name": "cittadini",
  "document_count": 6,
  "fields": [
    {
      "field_name": "codice_fiscale",
      "data_types": ["str"],
      "null_count": 0,
      "sample_values": ["RSSMRA85M01H501X", "BNCGLI90A41F205Y"]
    },
    {
      "field_name": "email_pec",
      "data_types": ["str"],
      "null_count": 0,
      "sample_values": ["mario.rossi@pec.regione.puglia.it"]
    },
    {
      "field_name": "comune_residenza",
      "data_types": ["str"],
      "null_count": 0,
      "sample_values": ["Bari", "Lecce", "Taranto"]
    }
  ],
  "size_bytes": 4096,
  "indexes": ["_id_", "codice_fiscale_1"]
}
```

**Caratteristiche:**
- Analizza fino a 100 documenti per prestazioni ottimali
- Rileva automaticamente i tipi di dati di ogni campo
- Conta i valori null per campo
- Fornisce valori di esempio (max 3 per campo)
- Converte ObjectId in stringhe per compatibilità JSON
- Elenca tutti gli indici della collezione

**Esempio di utilizzo:**
```bash
curl http://localhost:8000/collections/cittadini/metadata
```

---

### Endpoint 3: Estrazione Dati Collezione

**Descrizione:** Estrae i dati completi da una collezione con possibilità di limitare il numero di righe restituite tramite il parametro `max_righe`.

**Endpoint:**
```
GET /collections/{nome_collezione}/data?max_righe={n}
```

**Parametri:**
- `nome_collezione` (path): Nome della collezione da cui estrarre i dati
- `max_righe` (query, opzionale): Numero massimo di documenti da restituire

**Risposta:**
```json
{
  "collection_name": "cittadini",
  "data": [
    {
      "_id": "676541a2f1234567890abcde",
      "codice_fiscale": "RSSMRA85M01H501X",
      "nome": "Mario",
      "cognome": "Rossi",
      "email_pec": "mario.rossi@pec.regione.puglia.it",
      "comune_residenza": "Bari",
      "provincia": "BA",
      "cap": "70121"
    }
  ],
  "total_count": 6,
  "returned_count": 1,
  "max_righe": 1
}
```

**Comportamento:**
- Senza `max_righe`: restituisce tutti i documenti
- Con `max_righe`: limita il numero di documenti restituiti
- Converte ObjectId in stringhe per compatibilità JSON
- Mantiene l'ordine di inserimento dei documenti

**Esempi di utilizzo:**
```bash
# Estrarre tutti i dati
curl http://localhost:8000/collections/cittadini/data

# Limitare a 10 righe
curl http://localhost:8000/collections/cittadini/data?max_righe=10

# Limitare a 50 righe
curl http://localhost:8000/collections/servizi_pubblici/data?max_righe=50
```

---

### Endpoint 4: Validazione Query SQL

**Descrizione:** Valida la sintassi di query SQL per PostgreSQL, rileva errori comuni e restituisce la query formattata se valida.

**Endpoint:**
```
POST /sql/validate
```

**Body della richiesta:**
```json
{
  "query": "SELECT nome, cognome FROM cittadini WHERE provincia = 'BA'"
}
```

**Risposta (query valida):**
```json
{
  "valid": true,
  "query": "SELECT nome, cognome FROM cittadini WHERE provincia = 'BA'",
  "formatted_query": "SELECT nome,\n       cognome\nFROM cittadini\nWHERE provincia = 'BA'",
  "query_type": "SELECT",
  "error_message": null
}
```

**Risposta (query non valida):**
```json
{
  "valid": false,
  "query": "SELECT FROM cittadini",
  "formatted_query": null,
  "query_type": null,
  "error_message": "SELECT statement missing column list or * before FROM"
}
```

**Controlli di Validazione:**
- ✅ Sintassi SQL di base
- ✅ Presenza di colonne in SELECT
- ✅ Identificatori validi (non possono iniziare con '.')
- ✅ Operatori mancanti tra valori
- ✅ Pattern di SQL injection comuni
- ✅ Numeri consecutivi non separati
- ✅ Query vuote o solo spazi

**Esempi di utilizzo:**
```bash
# Query valida
curl -X POST http://localhost:8000/sql/validate \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM pratiche_amministrative WHERE stato = '\''approvata'\''"}'

# Query non valida
curl -X POST http://localhost:8000/sql/validate \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT FROM tabella"}'
```

---

## 🔧 Connessione a MongoDB Esterno

Per connettere l'API a un database MongoDB esistente (non in Docker):

### 1. Modificare il file `.env`

```env
MONGO_HOST=mongodb.regione.puglia.local
MONGO_PORT=27017
MONGO_DB=nome_database
MONGO_USER=username
MONGO_PASSWORD=password_sicura
```

### 2. Avviare l'API senza Docker

```bash
# Installare dipendenze Python
pip install -r requirements.txt

# Avviare il server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 🛠️ Sviluppo Locale (Senza Docker)

### Prerequisiti
- Python 3.11 o superiore
- MongoDB in esecuzione localmente o accessibile via rete

### Setup

1. **Installare le dipendenze:**
```bash
pip install -r requirements.txt
```

2. **Configurare le variabili d'ambiente:**

Modificare il file `.env`:
```env
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=testdb
MONGO_USER=
MONGO_PASSWORD=
```

3. **Avviare l'applicazione:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

4. **Popolare il database (opzionale):**
```bash
python scripts/seed_mongo.py
```

## 📊 Dati di Test

Lo script `seed_mongo.py` crea le seguenti collezioni con dati della Regione Puglia:

### 1. **cittadini** (6 documenti)
Dati anagrafici cittadini pugliesi:
- Campi: codice_fiscale, nome, cognome, email_pec, comune_residenza, provincia, cap
- Esempi: Bari, Lecce, Taranto, Foggia, Brindisi, Barletta

### 2. **servizi_pubblici** (6 documenti)
Servizi pubblici regionali:
- Campi: codice_servizio, nome_servizio, categoria, costo_euro, tempo_medio_giorni, ufficio_competente
- Esempi: Certificato residenza, Cambio residenza, Permesso ZTL, etc.

### 3. **pratiche_amministrative** (6 documenti)
Pratiche amministrative in corso:
- Campi: numero_pratica, codice_fiscale_richiedente, tipo_pratica, data_presentazione, stato, ufficio
- Esempi: Pratiche edilizie, concessioni, autorizzazioni commerciali

### 4. **vista_cittadini_per_comune** (view)
Vista aggregata che raggruppa i cittadini per comune di residenza

### 5. **vista_servizi_per_categoria** (view)
Vista aggregata che raggruppa i servizi pubblici per categoria

### 6. **metriche_accessi** (timeseries)
Collezione timeseries per tracciare gli accessi ai servizi pubblici

## 📦 Librerie e Tecnologie Utilizzate

### Backend Framework
- **FastAPI 0.109.0**
  - Framework web moderno per Python con supporto asincrono
  - Generazione automatica di documentazione OpenAPI/Swagger
  - Validazione automatica dei dati tramite Pydantic
  - Alte prestazioni grazie all'architettura ASGI

### Server ASGI
- **Uvicorn 0.27.0**
  - Server ASGI ad alte prestazioni per Python
  - Supporto hot-reload per sviluppo rapido
  - Gestione efficiente di connessioni asincrone

### Database Driver
- **PyMongo 4.6.1**
  - Driver ufficiale MongoDB per Python
  - Supporto completo per aggregation pipeline
  - Gestione connessioni con connection pooling
  - Supporto per tutte le operazioni CRUD

### Validazione Dati
- **Pydantic 2.5.3**
  - Validazione automatica dei dati tramite type hints Python
  - Serializzazione/deserializzazione JSON
  - Generazione automatica di schemi JSON
  - Gestione errori di validazione dettagliata

### Parsing SQL
- **sqlparse 0.4.4**
  - Parser SQL per Python con supporto multi-dialetto
  - Formattazione automatica query SQL
  - Analisi sintattica e rilevamento errori
  - Supporto per PostgreSQL, MySQL, SQLite

### Gestione Configurazione
- **python-dotenv 1.0.0**
  - Caricamento variabili d'ambiente da file .env
  - Gestione configurazioni sensibili
  - Separazione configurazioni per ambiente (dev/prod)

### Containerizzazione
- **Docker & Docker Compose**
  - Isolamento ambiente di esecuzione
  - Orchestrazione multi-container (API + MongoDB)
  - Portabilità tra ambienti diversi
  - MongoDB 7.0.14 come database engine

## 🌐 Variabili d'Ambiente

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `MONGO_HOST` | Hostname o IP del server MongoDB | `mongodb` |
| `MONGO_PORT` | Porta di MongoDB | `27017` |
| `MONGO_DB` | Nome del database | `testdb` |
| `MONGO_USER` | Username MongoDB (opzionale) | `` |
| `MONGO_PASSWORD` | Password MongoDB (opzionale) | `` |

## 🐳 Comandi Docker Utili

```bash
# Costruire l'immagine
docker build -t mongo-fastapi:latest .

# Avviare i servizi
docker-compose up -d

# Visualizzare i log
docker-compose logs -f

# Visualizzare log solo dell'API
docker-compose logs -f fastapi

# Visualizzare log solo di MongoDB
docker-compose logs -f mongodb

# Fermare i servizi
docker-compose down

# Fermare e rimuovere volumi
docker-compose down -v

# Ricostruire e riavviare
docker build -t mongo-fastapi:latest . && docker-compose down && docker-compose up -d

# Accedere al container FastAPI
docker-compose exec fastapi bash

# Accedere a MongoDB Shell
docker-compose exec mongodb mongosh testdb

# Verificare stato servizi
docker-compose ps

# Verificare salute container
docker-compose ps -a
```

## 🔍 Test e Verifica

### Verificare che l'API sia attiva

```bash
curl http://localhost:8000/
```

Risposta attesa:
```json
{
  "message": "MongoDB FastAPI is running",
  "version": "1.0.0",
  "database": "testdb"
}
```

### Testare tutti gli endpoint

```bash
# 1. Elenco collezioni
curl http://localhost:8000/collections/

# 2. Metadati collezione
curl http://localhost:8000/collections/cittadini/metadata

# 3. Dati collezione (limitati)
curl http://localhost:8000/collections/cittadini/data?max_righe=2

# 4. Validazione SQL
curl -X POST http://localhost:8000/sql/validate \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM cittadini WHERE provincia = '\''BA'\''"}'
```

## 📝 Note Tecniche

- Il parametro `max_righe` è in italiano come da requisiti ("massimo righe" = "maximum rows")
- Gli ObjectId di MongoDB (`_id`) vengono automaticamente convertiti in stringhe per compatibilità JSON
- I metadati delle collezioni sono generati analizzando fino a 100 documenti per ottimizzare le prestazioni
- L'API gestisce correttamente valori null e campi mancanti
- Le view MongoDB sono di sola lettura e basate su aggregation pipeline
- Le collezioni timeseries sono ottimizzate per dati con timestamp sequenziali
- Le collezioni capped hanno dimensione fissa e comportamento FIFO (First In First Out)
- Hot-reload attivo in sviluppo: le modifiche al codice Python vengono applicate automaticamente senza rebuild

## 🔐 Sicurezza

- Le credenziali MongoDB sono gestite tramite variabili d'ambiente
- Il file `.env` contiene informazioni sensibili e non deve essere committato
- L'endpoint di validazione SQL rileva pattern di SQL injection comuni
- MongoDB Connection String supporta autenticazione con username/password
- Consigliato l'uso di network Docker isolate in produzione

## 📞 Supporto

Per assistenza tecnica o domande sul progetto:
- **Cliente:** Regione Puglia - Ente Governativo
- **Sviluppatore:** Giovanni Brucoli
- **Email:** giopantana@gmail.com
- **GitHub:** @dataappengineer

## 📄 Licenza

MIT License - Sviluppato per Regione Puglia
