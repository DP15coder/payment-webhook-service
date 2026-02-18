from datetime import datetime

from sqlalchemy import Column, String, Numeric, DateTime, Enum

from .database import Base
import enum


class TransactionStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True, index=True)
    source_account = Column(String, nullable=False)
    destination_account = Column(String, nullable=False)
    amount = Column(Numeric(precision=18, scale=2), nullable=False)
    currency = Column(String(10), nullable=False)

    status = Column(
        Enum(TransactionStatus, native_enum=False, length=16),
        nullable=False,
        default=TransactionStatus.PROCESSING,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

