# Enterprise Inventory Orchestrator

This project is a backend application built using FastAPI to manage inventory data and handle bulk stock reconciliation. It includes API key authentication, asynchronous processing, database transaction handling, and reconciliation audit logs.


## Technologies Used

- Python
- FastAPI
- SQLAlchemy (Async)
- SQLite
- Pydantic
- Pytest
- Docker
- Docker Compose

## Project Structure

inventory-orchstrator/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── seed.py
│   ├── routers/
│   │   └── inventory.py
│   └── services/
│       ├── sync_worker.py
│       └── utils.py
├── tests/
│   └── test_inventory.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md


## Running Locally

### 1. Clone the repository

```bash
git clone <repository-url>
cd inventory-orchstrator
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
APP_NAME=Enterprise Inventory Orchestrator
DATABASE_URL=sqlite+aiosqlite:///./enterprise_inventory.db
API_KEY_SECRET=your-secret-api-key
```

### 5. Initialize sample data

```bash
python -m app.seed
```

### 6. Start the server

```bash
python -m uvicorn app.main:app --reload
```

The application runs at:

`http://localhost:8000`

Swagger UI:

`http://localhost:8000/docs`

## Running with Docker

Build and start the application using Docker Compose:

```bash
docker compose up --build
```

To stop the containers:

```bash
docker compose down
```

The project includes a Dockerfile for building the application image and a Docker Compose configuration for running the service.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check application health |
| GET | `/api/v1/inventory` | Get inventory items |
| GET | `/api/v1/inventory/products/{sku}` | Get a product by SKU |
| POST | `/api/v1/inventory/reconcile` | Submit a reconciliation request |
| GET | `/api/v1/inventory/audit-logs` | Get reconciliation audit logs |

## Authentication

All endpoints except `/health` require an API key.

Include the following header in your request:

```http
X-Api-Key: your-secret-api-key
```

Example:

```bash
curl -H "X-Api-Key: your-secret-api-key" http://localhost:8000/api/v1/inventory
```

## Inventory Pagination and Filtering

The inventory endpoint supports the following query parameters:

| Parameter   | Description                         | Default |
|---          |---                                  |---      |
| `limit`     | Number of items to return (1–100)   | 10      |
| `offset`    | Number of items to skip             | 0       |
| `min_stock` | Filter by minimum stock quantity    | None    |
| `is_active` | Filter by active status             | true    |

Example:

```http
GET /api/v1/inventory?limit=10&offset=0&min_stock=5&is_active=true
```

## Inventory Reconciliation

Example request:

```json
{
  "items": [
    {
      "sku": "LAPTOP001",
      "stock_quantity": 45
    },
    {
      "sku": "MOUSE001",
      "stock_quantity": 100
    }
  ]
}
```

The API returns `202 Accepted` after receiving the request and schedules the reconciliation using FastAPI BackgroundTasks.

### How reconciliation works

1. The request is validated using Pydantic.
2. Duplicate SKUs are rejected with HTTP `422`.
3. The reconciliation task runs in the background.
4. The worker checks whether all requested SKUs exist.
5. Stock quantities are updated within a database transaction.
6. An audit log is recorded based on the outcome.

### Important decisions

- **Transaction handling:** All stock updates in a request are committed together. If an SKU is unknown, the transaction is rolled back.
- **Duplicate SKUs:** Duplicate entries are rejected before processing.
- **Unknown SKUs:** The reconciliation fails without partially updating inventory.
- **Audit logs:** Each reconciliation outcome is recorded with its status, timestamp, processed SKU count, and error details when applicable.
- **Database lock handling:** SQLite lock errors are retried up to three times.
- **Retry fallback:** If retries are exhausted, a `RETRY_FALLBACK` audit status is recorded.
- **Successful reconciliation:** Stock updates and their success audit are committed together.

## Technical Notes

### Background processing

FastAPI BackgroundTasks is used to process reconciliation after the API accepts the request. This allows the client to receive a response without waiting for the complete stock update operation.

### Database transactions

SQLAlchemy transactions are used to maintain consistency during reconciliation. If an operation fails, changes within the transaction are rolled back.

### SQLite concurrency

SQLite supports concurrent reads but can encounter locking when multiple write operations happen at the same time. The worker handles temporary lock errors with a retry mechanism.

### Configuration

Pydantic Settings loads application configuration from environment variables and the `.env` file. This keeps configuration separate from application code.

### Logging

Application events are logged in JSON format with timestamps and relevant details to make debugging easier.

## Running Tests

Run the tests using:

```bash
python -m pytest -v
```

The test suite checks API authentication, inventory pagination, the health endpoint, reconciliation behavior, and audit logging, including validation of duplicate and unknown SKUs.

All 10 tests are currently passing.

