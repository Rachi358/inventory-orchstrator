# Enterprise Inventory Orchestrator

Enterprise Inventory Orchestrator is a backend application developed using FastAPI to manage inventory records and process bulk stock reconciliation. It includes API key authentication, asynchronous background processing, database transactions, retry handling, and audit logging.

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

```text
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
```

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/Rachi358/inventory-orchstrator.git
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

### 5. Initialize the database and sample data

```bash
python -m app.seed
```

### 6. Start the server

```bash
python -m uvicorn app.main:app --reload
```

The application will be available at:

- Application: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

## Running with Docker

Build and start the application using Docker Compose:

```bash
docker compose up --build
```

To stop the containers:

```bash
docker compose down
```

The project includes a multi-stage Dockerfile and a Docker Compose configuration for containerized deployment. SQLite data is persisted using a Docker named volume.

### Verify the Docker Deployment

Check the health endpoint:

```bash
curl http://localhost:8000/health
```

Access the inventory endpoint using the configured API key:

```bash
curl -H "X-Api-Key: docker-development-secret" \
     http://localhost:8000/api/v1/inventory
```

Replace `docker-development-secret` with your configured `API_KEY_SECRET` if it differs from the Docker Compose default.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check application health |
| GET | `/api/v1/inventory` | Retrieve paginated inventory |
| GET | `/api/v1/inventory/products/{sku}` | Retrieve a product by SKU |
| POST | `/api/v1/inventory/reconcile` | Submit a stock reconciliation request |
| GET | `/api/v1/inventory/audit-logs` | Retrieve reconciliation audit logs |

## Authentication

All endpoints except `/health` require API key authentication.

Include the following header in your request:

```http
X-Api-Key: your-secret-api-key
```

Example:

```bash
curl -H "X-Api-Key: your-secret-api-key" \
     http://localhost:8000/api/v1/inventory
```

The API key is configured through the `API_KEY_SECRET` environment variable.

## Inventory Pagination and Filtering

The inventory endpoint supports the following query parameters:

| Parameter | Description | Default |
|---|---|---|
| `limit` | Number of items to return (1–100) | 10 |
| `offset` | Number of items to skip | 0 |
| `min_stock` | Filter by minimum stock quantity | None |
| `is_active` | Filter by active status | true |

Example:

```http
GET /api/v1/inventory?limit=10&offset=0&min_stock=5&is_active=true
```

## Inventory Reconciliation

### Example Request

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

The API returns `202 Accepted` after receiving the request and schedules the reconciliation task using FastAPI `BackgroundTasks`.

### Reconciliation Workflow

1. The incoming request is validated using Pydantic.
2. Duplicate SKUs are rejected with HTTP `422`.
3. The reconciliation task is scheduled for background processing.
4. The worker verifies that the requested SKUs exist in the database.
5. Stock quantities are updated within a database transaction.
6. An audit log is recorded based on the reconciliation outcome.

### Design Decisions

- **Transaction handling:** All stock updates within a request are committed together. If an SKU is unknown, the transaction is rolled back.
- **Duplicate SKUs:** Duplicate entries are rejected during request validation before processing.
- **Unknown SKUs:** Reconciliation fails without partially updating inventory.
- **Audit logging:** Each reconciliation outcome is recorded with its status, timestamp, processed SKU count, and error details when applicable.
- **Database lock handling:** SQLite lock errors are retried up to three times to handle temporary database contention.
- **Retry fallback:** If all retry attempts fail, a `RETRY_FALLBACK` audit status is recorded, preserving the final reconciliation outcome.
- **Successful reconciliation:** Inventory updates and their success audit record are committed together.

## Technical Notes

### Background Processing and Concurrency

FastAPI `BackgroundTasks` allows the reconciliation request to return `202 Accepted` without waiting for stock updates to finish.

The worker uses SQLAlchemy database transactions to ensure that stock updates within a reconciliation request are committed together. SQLite write-lock errors are handled through a retry mechanism with up to three attempts. If reconciliation fails, the transaction is rolled back and the outcome is recorded in the audit log.

### Database Transactions

SQLAlchemy transactions maintain data consistency during reconciliation. If an operation fails, changes made within the transaction are rolled back.

### SQLite Concurrency

SQLite supports concurrent reads but may encounter locking during simultaneous write operations. The reconciliation worker handles temporary database lock errors using a retry mechanism.

### Configuration Management

Pydantic Settings loads application configuration from environment variables and the `.env` file. This keeps configuration separate from application code.

### Logging

Application events are recorded using structured JSON logs containing timestamps and relevant details, making application monitoring and debugging easier.

## Running Tests

Run the test suite using:

```bash
python -m pytest -v
```

The tests cover API authentication, inventory pagination, the health endpoint, reconciliation behavior, and audit logging, including duplicate and unknown SKU validation.
