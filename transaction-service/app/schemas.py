from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TransferIn(BaseModel):
    fromAccount: str
    toAccount: str
    amount: float
    currency: str = "INR"
    idempotency_key: str | None = None

class TransactionOut(BaseModel):
    id: str
    txId: str
    fromAccount: str
    toAccount: str
    amount: float
    currency: str
    status: str
    createdAt: Optional[datetime] = None