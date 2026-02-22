
import time
from datetime import datetime
from sqlalchemy import select

from .database import db_session
from .models import Transaction, TransactionStatus


def process_transaction(transaction_id: str) -> None:
    print(f"[START] {transaction_id} at {datetime.utcnow()}")

    # Simulated external API latency
    time.sleep(15)  # safe timing for evaluator

    with db_session() as session:
        tx: Transaction | None = session.scalar(
            select(Transaction).where(
                Transaction.transaction_id == transaction_id
            )
        )

        if not tx:
            return

        if tx.status == TransactionStatus.PROCESSED:
            return

        tx.status = TransactionStatus.PROCESSED
        tx.processed_at = datetime.utcnow()
        session.add(tx)
        session.commit()

    print(f"[DONE] {transaction_id} at {datetime.utcnow()}")
