from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List

from .config import get_settings
from .database import Base, engine, get_db
from .models import Transaction, TransactionStatus
from .schemas import (
    HealthCheckOut,
    TransactionOut,
    WebhookTransactionIn,
)
from .worker import enqueue_transaction_processing


settings = get_settings()

app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def on_startup() -> None:
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)


@app.get("/", response_model=HealthCheckOut)
def health_check() -> HealthCheckOut:
    """
    Simple health check endpoint.
    """
    return HealthCheckOut(status="HEALTHY", current_time=datetime.utcnow())


@app.post(
    f"{settings.api_prefix}/webhooks/transactions",
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_transaction_webhook(
    payload: WebhookTransactionIn,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Accept transaction webhooks and enqueue background processing.
    Must return 202 quickly while processing happens in the background.
    Idempotent on transaction_id.
    """
    existing: Transaction | None = db.scalar(
        select(Transaction).where(
            Transaction.transaction_id == payload.transaction_id
        )
    )

    if existing:
        # Already seen this transaction_id; ensure it's at least in PROCESSING state
        if existing.status == TransactionStatus.PROCESSING:
            # processing already underway; just acknowledge
            pass
        elif existing.status == TransactionStatus.PROCESSED:
            # already processed; nothing to do
            pass
        else:
            # FAILED or another state: we could choose to re-enqueue if desired
            enqueue_transaction_processing(existing.transaction_id)

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
        # In case of a race, treat as already received
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"message": "Transaction already received"},
        )

    # enqueue background processing (returns immediately)
    enqueue_transaction_processing(tx.transaction_id)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"message": "Transaction accepted for processing"},
    )


# @app.get(
#     f"{settings.api_prefix}/transactions/{{transaction_id}}",
#     response_model=TransactionOut,
# )
# def get_transaction_status(
#     transaction_id: str,
#     db: Session = Depends(get_db),
# ) -> TransactionOut:
#     """
#     Retrieve transaction status and timing info.
#     """
#     tx: Transaction | None = db.scalar(
#         select(Transaction).where(Transaction.transaction_id == transaction_id)
#     )

#     if not tx:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

#     return TransactionOut.model_validate(tx)

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