## Transaction Webhook Service

Python/FastAPI service for processing payment transaction webhooks in the background with strict 500ms response-time for the webhook endpoint, idempotency guarantees, and persistent storage.

### High-level Architecture

- **FastAPI App**: Exposes three endpoints:
  - `GET /` — health check.
  - `POST /v1/webhooks/transactions` — accepts transaction webhooks and **always responds with 202 within 500ms**, regardless of processing time.
  - `GET /v1/transactions/{transaction_id}` — fetches transaction status for testing.
- **Background Worker (RQ + Redis)**:
  - Webhook handler enqueues a job to process each transaction on a Redis-backed RQ queue.
  - Dedicated worker process executes `process_transaction()`:
    - Simulates a 30-second delay (to mimic a heavy external API call).
    - Marks the transaction as `PROCESSED` with `processed_at` timestamp.
  - **Idempotent**: if the same `transaction_id` is enqueued multiple times, only the first insert succeeds and later requests are treated as duplicates.
- **Database (SQLAlchemy)**:
  - Stores transactions with fields required by the problem statement.
  - Can use **SQLite for local development** and **PostgreSQL** (or any cloud DB that supports SQLAlchemy) in production via `DATABASE_URL` env var.
- **Config**:
  - Managed via environment variables in `app/config.py` (`DATABASE_URL`, `REDIS_URL`, `ENVIRONMENT`).

### Data Model

`Transaction` table:
- `transaction_id` (PK, string)
- `source_account` (string)
- `destination_account` (string)
- `amount` (decimal, 2dp)
- `currency` (string)
- `status` (`PROCESSING` | `PROCESSED` | `FAILED`)
- `created_at` (datetime, UTC)
- `processed_at` (nullable datetime, UTC)

### Local Setup

#### 1. Create virtual env & install dependencies

```bash
cd confluncer-assignment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2. Start Redis

You need Redis locally (or a managed Redis).

- **macOS (Homebrew)**:

```bash
brew install redis
brew services start redis
```

Or point `REDIS_URL` to your managed Redis instance.

#### 3. Environment variables

Create a `.env` file (optional) and export:

```bash
export DATABASE_URL="sqlite:///./transactions.db"  # or your Postgres URL
export REDIS_URL="redis://localhost:6379/0"
export ENVIRONMENT="local"
```

#### 4. Run API server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 5. Run background worker

In a second terminal:

```bash
rq worker transactions --url "$REDIS_URL"
```

This worker listens to the `transactions` queue and runs `process_transaction()` for each job.

### Testing the Flows

#### 1. Health check

```bash
curl http://localhost:8000/
```

#### 2. Single transaction test

```bash
curl -X POST http://localhost:8000/v1/webhooks/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "txn_abc123def456",
    "source_account": "acc_user_789",
    "destination_account": "acc_merchant_456",
    "amount": 150.50,
    "currency": "INR"
  }'
```

You should receive `202 Accepted` immediately.
After ~30 seconds, query the status:

```bash
curl http://localhost:8000/v1/transactions/txn_abc123def456
```

The response should show:
- `status`: `PROCESSED`
- `processed_at`: non-null timestamp

#### 3. Duplicate prevention test

Send the same webhook multiple times quickly (same `transaction_id`).

```bash
for i in {1..3}; do
  curl -X POST http://localhost:8000/v1/webhooks/transactions \
    -H "Content-Type: application/json" \
    -d '{
      "transaction_id": "txn_dup123",
      "source_account": "acc_user_789",
      "destination_account": "acc_merchant_456",
      "amount": 999.99,
      "currency": "INR"
    }';
done
```

Only one row is stored in the DB (`transaction_id` is primary key), and processing occurs once.

#### 4. Performance check

Because:
- The webhook handler only does a quick DB write and enqueues to Redis, and
- All heavy work (30s delay) runs in the worker,

the `POST /v1/webhooks/transactions` endpoint consistently responds well under **500ms**, even under load (actual performance depends on your environment).

### Deployment to Railway

## Deployed  URL 
https://transaction-api-production-714a.up.railway.app/

Services Used

- transaction-api → FastAPI web service
- transaction-worker → RQ background worker
- transaction-db → PostgreSQL database

 Redis → Managed Redis instance

- Railway Environment Variables
- For transaction-api and transaction-worker:
- DATABASE_URL=${{transaction-db.DATABASE_URL}}
-REDIS_URL=<your-redis-connection-s