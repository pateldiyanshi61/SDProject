from pydantic import BaseModel, Field
from typing import Optional

class AccountCreate(BaseModel):
    accountNumber: str
    userId: str
    balance: float = 0.0
    currency: str = "INR"
    status: str = "active"
    meta: Optional[dict] = None

class AccountOut(AccountCreate):
    id: str

class AccountUpdate(BaseModel):
    balance: Optional[float]
    status: Optional[str]
    meta: Optional[dict]
