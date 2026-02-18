import time
from datetime import datetime

from rq import Queue
from redis import Redis
from sqlalchemy import select

from .config import get_settings
from .database import db_session
from .models import Transaction, TransactionStatus


settings = get_settings()
redis_conn = Redis.from_url(settings.redis_url)
queue = Queue("transactions", connection=redis_conn, default_timeout=60)


def enqueue_transaction_processing(transaction_id: str) -> None:
    """
    Enqueue a background job to process a transaction.
    """
    queue.enqueue(process_transaction, transaction_id)


def process_transaction(transaction_id: str) -> None:
    """
    Simulate slow processing with a 30s delay and then mark transaction as processed.
    Idempotent: if transaction is already PROCESSED/FAILED, it is left unchanged.
    """
    # simulate external API latency
    time.sleep(30)

    with db_session() as session:
        tx: Transaction | None = session.scalar(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        )

        if not tx:
            return

        if tx.status == TransactionStatus.PROCESSED:
            return

        tx.status = TransactionStatus.PROCESSED
        tx.processed_at = datetime.utcnow()
        session.add(tx)

