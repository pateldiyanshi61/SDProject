from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# ============================
#    TRANSACTION SCHEMAS
# ============================

class DepositIn(BaseModel):
    """Schema for depositing money into an account"""
    accountNumber: str = Field(..., description="Account number to deposit into")
    amount: float = Field(..., gt=0, description="Amount to deposit (must be positive)")
    currency: str = Field(default="USD", description="Currency code")
    description: Optional[str] = Field(None, description="Optional description for the deposit")

class WithdrawIn(BaseModel):
    """Schema for withdrawing money from an account"""
    accountNumber: str = Field(..., description="Account number to withdraw from")
    amount: float = Field(..., gt=0, description="Amount to withdraw (must be positive)")
    currency: str = Field(default="USD", description="Currency code")
    description: Optional[str] = Field(None, description="Optional description for the withdrawal")

class TransferIn(BaseModel):
    """Schema for transferring money between accounts"""
    fromAccount: str = Field(..., description="Source account number")
    toAccount: str = Field(..., description="Destination account number")
    amount: float = Field(..., gt=0, description="Amount to transfer (must be positive)")
    currency: str = Field(default="USD", description="Currency code")

class TransactionOut(BaseModel):
    """Schema for transaction output"""
    id: str
    txId: str
    fromAccount: str
    toAccount: str
    amount: float
    currency: str
    status: str
    type: Optional[str] = None
    description: Optional[str] = None
    createdAt: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }