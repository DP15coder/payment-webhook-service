
from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .database import Base, engine, get_db
from .models import Transaction, TransactionStatus
from .schemas import (
    HealthCheckOut,
    TransactionOut,
    WebhookTransactionIn,
)
from .worker import process_transaction


settings = get_settings()

app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/", response_model=HealthCheckOut)
def health_check() -> HealthCheckOut:
    return HealthCheckOut(status="HEALTHY", current_time=datetime.utcnow())


@app.post(
    f"{settings.api_prefix}/webhooks/transactions",
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_transaction_webhook(
    payload: WebhookTransactionIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JSONResponse:

    existing: Transaction | None = db.scalar(
        select(Transaction).where(
            Transaction.transaction_id == payload.transaction_id
        )
    )

    if existing:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"message": "Transaction already received"},
        )

    tx = Transaction(
        transaction_id=payload.transaction_id,
        source_account=payload.source_account,
        destination_account=payload.destination_account,
        amount=payload.amount,
        currency=payload.currency,
        status=TransactionStatus.PROCESSING,
    )

    db.add(tx)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"message": "Transaction already received"},
        )

    # Background task instead of RQ enqueue
    background_tasks.add_task(process_transaction, tx.transaction_id)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"message": "Transaction accepted for processing"},
    )


@app.get(
    f"{settings.api_prefix}/transactions/{{transaction_id}}",
    response_model=List[TransactionOut],
)
def get_transaction_status(
    transaction_id: str,
    db: Session = Depends(get_db),
) -> List[TransactionOut]:

    tx: Transaction | None = db.scalar(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    )

    if not tx:
        return []

    return [TransactionOut.model_validate(tx)]
