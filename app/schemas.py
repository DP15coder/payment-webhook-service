from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, condecimal


class WebhookTransactionIn(BaseModel):
    transaction_id: str = Field(..., examples=["txn_abc123def456"])
    source_account: str
    destination_account: str
    amount: condecimal(max_digits=18, decimal_places=2)  # type: ignore[type-arg]
    currency: str


class TransactionOut(BaseModel):
    transaction_id: str
    source_account: str
    destination_account: str
    amount: condecimal(max_digits=18, decimal_places=2)  # type: ignore[type-arg]
    currency: str
    status: str
    created_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class HealthCheckOut(BaseModel):
    status: str
    current_time: datetime

