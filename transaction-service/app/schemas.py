from pydantic import BaseModel

class TransferIn(BaseModel):
    fromAccount: str
    toAccount: str
    amount: float
    currency: str = "INR"
    idempotency_key: str | None = None
