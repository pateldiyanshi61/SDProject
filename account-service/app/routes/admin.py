from fastapi import APIRouter, HTTPException
from ..db import accounts
router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/freeze-account")
async def freeze_account(accountNumber: str, freeze: bool = True):
    status = "frozen" if freeze else "active"
    res = await accounts.update_one({"accountNumber": accountNumber}, {"$set": {"status": status}})
    if res.matched_count == 0:
        raise HTTPException(404, "account not found")
    return {"accountNumber": accountNumber, "status": status}

@router.get("/stats")
async def stats():
    total_users = await accounts.database.users.count_documents({})
    total_accounts = await accounts.count_documents({})
    total_txns = await accounts.database.transactions.count_documents({})
    return {"users": total_users, "accounts": total_accounts, "transactions": total_txns}
