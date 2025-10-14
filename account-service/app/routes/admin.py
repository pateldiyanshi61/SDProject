from fastapi import APIRouter, HTTPException, Depends
from ..db import accounts
from ..auth import verify_token

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/freeze-account")
async def freeze_account(accountNumber: str, freeze: bool = True, user=Depends(verify_token)):
    # Only admin can freeze accounts
    if user.get("role") != "admin":
        raise HTTPException(403, "Forbidden: admin only")
    
    status = "frozen" if freeze else "active"
    res = await accounts.update_one({"accountNumber": accountNumber}, {"$set": {"status": status}})
    if res.matched_count == 0:
        raise HTTPException(404, "account not found")
    return {"accountNumber": accountNumber, "status": status}

@router.get("/stats")
async def stats(user=Depends(verify_token)):
    # Only admin can view stats
    if user.get("role") != "admin":
        raise HTTPException(403, "Forbidden: admin only")
    
    total_users = await accounts.database.users.count_documents({})
    total_accounts = await accounts.count_documents({})
    total_txns = await accounts.database.transactions.count_documents({})
    return {"users": total_users, "accounts": total_accounts, "transactions": total_txns}