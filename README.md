# MongoDB FastAPI REST API

REST API built with FastAPI and PyMongo to interact with MongoDB collections. Provides three main endpoints to list collections, retrieve metadata, and fetch collection data.

## Features

✅ **3 Core Endpoints:**
1. List all MongoDB collections
2. Get collection metadata (fields, data types, document count, indexes)
3. Retrieve collection data with optional row limit (`max_righe`)

✅ **Plug and Play:** Works with both Docker MongoDB (`mongo:7.0.14`) and external MongoDB deployments

✅ **Docker Ready:** Complete Docker Compose setup included

✅ **Test Data:** Seed script to populate MongoDB with sample collections

## Project Structure

```
mongo-fastAPI/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── database.py          # MongoDB connection
│   ├── models.py            # Pydantic response models
│   └── routers/
│       ├── __init__.py
│       └── collections.py   # Collection endpoints
├── scripts/
│   └── seed_mongo.py        # Database seeding script
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # FastAPI container
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
└── README.md
```

## Quick Start with Docker

### 1. Start the services

```bash
docker-compose up -d
```

This will start:
- MongoDB on port 27017 (image: `mongo:7.0.14`)
- FastAPI on port 8000

### 2. Seed the database with test data

```bash
docker-compose exec fastapi python scripts/seed_mongo.py
```

This creates three collections: `customers`, `products`, and `orders` with sample data.

### 3. Access the API

- **API Base URL:** http://localhost:8000
- **Interactive Docs:** http://localhost:8000/docs
- **OpenAPI Schema:** http://localhost:8000/openapi.json

## API Endpoints

### 1. List Collections

```bash
GET /collections/
```

**Response:**
```json
{
  "collections": ["customers", "products", "orders"],
  "count": 3
}
```

**Example:**
```bash
curl http://localhost:8000/collections/
```

### 2. Get Collection Metadata

```bash
GET /collections/{collection_name}/metadata
```

**Response:**
```json
{
  "collection_name": "customers",
  "document_count": 5,
  "fields": [
    {
      "field_name": "customer_id",
      "data_types": ["int"],
      "null_count": 0,
      "sample_values": [1, 2, 3]
    },
    {
      "field_name": "name",
      "data_types": ["str"],
      "null_count": 0,
      "sample_values": ["Mario Rossi", "Giulia Bianchi"]
    }
  ],
  "size_bytes": 2048,
  "indexes": ["_id_", "customer_id_1", "email_1"]
}
```

**Example:**
```bash
curl http://localhost:8000/collections/customers/metadata
```

### 3. Get Collection Data

```bash
GET /collections/{collection_name}/data?max_righe={n}
```

**Query Parameters:**
- `max_righe` (optional): Maximum number of rows to return (Italian: "massimo righe")

**Response:**
```json
{
  "collection_name": "customers",
  "data": [
    {
      "_id": "64a1b2c3d4e5f6g7h8i9j0k1",
      "customer_id": 1,
      "name": "Mario Rossi",
      "email": "mario.rossi@email.it",
      "age": 35,
      "city": "Roma",
      "active": true
    }
  ],
  "total_count": 5,
  "returned_count": 1,
  "max_righe": 1
}
```

**Examples:**
```bash
# Get all data
curl http://localhost:8000/collections/customers/data

# Limit to 3 rows
curl http://localhost:8000/collections/customers/data?max_righe=3
```

## Connecting to External MongoDB

To connect the API to your own MongoDB deployment (not Docker):

### 1. Update `.env` file

```env
MONGO_HOST=your-mongo-host.com
MONGO_PORT=27017
MONGO_DB=your-database-name
MONGO_USER=your-username
MONGO_PASSWORD=your-password
```

### 2. Run without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Local Development (Without Docker)

### Prerequisites
- Python 3.11+
- MongoDB running locally or remotely

### Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**

Edit `.env` file with your MongoDB settings:
```env
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=testdb
MONGO_USER=
MONGO_PASSWORD=
```

3. **Run the application:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

4. **Seed test data (optional):**
```bash
python scripts/seed_mongo.py
```

## Test Collections

The seed script creates three collections with test data:

### 1. **customers** (5 documents)
- Fields: customer_id, name, email, age, city, active, registration_date, total_purchases
- Includes null value test case (missing age)

### 2. **products** (5 documents)
- Fields: product_id, name, category, price, in_stock, quantity, specs (nested), tags (array)
- Includes null nested object test case

### 3. **orders** (5 documents)
- Fields: order_id, customer_id, order_date, status, items (array), total_amount, shipping_address (nested)
- Includes null nested object test case

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_HOST` | MongoDB host | `localhost` |
| `MONGO_PORT` | MongoDB port | `27017` |
| `MONGO_DB` | Database name | `testdb` |
| `MONGO_USER` | Username (optional) | `` |
| `MONGO_PASSWORD` | Password (optional) | `` |

## Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild containers
docker-compose up -d --build

# Access FastAPI container
docker-compose exec fastapi bash

# Access MongoDB container
docker-compose exec mongodb mongosh
```

## Technology Stack

- **FastAPI** - Modern Python web framework
- **PyMongo** - MongoDB driver for Python
- **Pydantic** - Data validation using Python type hints
- **Uvicorn** - ASGI server
- **Docker** - Containerization
- **MongoDB 7.0.14** - NoSQL database

## API Documentation

Once the application is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Notes

- The `max_righe` parameter is in Italian as requested ("massimo righe" = "maximum rows")
- MongoDB `_id` fields are converted to strings in API responses for JSON compatibility
- Collection metadata is generated by sampling up to 100 documents for performance
- The API handles null values and missing fields gracefully

## License

MIT

## Author

Giovanni Brucoli (@dataappengineer)
