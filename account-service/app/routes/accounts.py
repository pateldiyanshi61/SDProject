from fastapi import APIRouter, HTTPException, Query, Depends
from bson import ObjectId
from ..db import accounts
from ..schemas import AccountCreate, AccountOut, AccountUpdate
from ..auth import verify_token

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

@router.post("", response_model=AccountOut)
async def create_account(payload: AccountCreate, user=Depends(verify_token)):
    # Only admin can create accounts for others
    if user.get("role") != "admin" and payload.userId != user.get("user_id"):
        raise HTTPException(403, "Forbidden: cannot create account for another user")
    
    if await accounts.find_one({"accountNumber": payload.accountNumber}):
        raise HTTPException(400, "accountNumber exists")
    
    res = await accounts.insert_one(payload.model_dump())
    acc = await accounts.find_one({"_id": res.inserted_id})
    return {"id": str(acc["_id"]), **{k:v for k,v in acc.items() if k!="_id"}}

@router.get("", response_model=list[AccountOut])
async def list_accounts(user_id: str | None = None, user=Depends(verify_token)):
    # Admin can see all accounts, users can only see their own
    if user.get("role") != "admin":
        user_id = user.get("user_id")
    
    q = {}
    if user_id:
        q["userId"] = user_id
    
    cur = accounts.find(q)
    result = []
    async for a in cur:
        a["id"] = str(a["_id"])
        a.pop("_id", None)
        result.append(a)
    return result

@router.get("/{account_id}", response_model=AccountOut)
async def get_account(account_id: str, user=Depends(verify_token)):
    a = await accounts.find_one({"_id": ObjectId(account_id)})
    if not a:
        raise HTTPException(404, "not found")
    
    # Check authorization
    if user.get("role") != "admin" and a.get("userId") != user.get("user_id"):
        raise HTTPException(403, "Forbidden")
    
    a["id"] = str(a["_id"])
    a.pop("_id", None)
    return a

@router.get("/{account_id}/balance")
async def get_balance(account_id: str, user=Depends(verify_token)):
    a = await accounts.find_one({"_id": ObjectId(account_id)})
    if not a:
        raise HTTPException(404, "not found")
    
    # Check authorization
    if user.get("role") != "admin" and a.get("userId") != user.get("user_id"):
        raise HTTPException(403, "Forbidden")
    
    return {
        "accountId": str(a["_id"]),
        "accountNumber": a.get("accountNumber"),
        "balance": a.get("balance", 0.0),
        "currency": a.get("currency", "INR")
    }

@router.put("/{account_id}", response_model=AccountOut)
async def update_account(account_id: str, payload: AccountUpdate, user=Depends(verify_token)):
    # Only admin can update accounts
    if user.get("role") != "admin":
        raise HTTPException(403, "Forbidden: admin only")
    
    upd = {k:v for k,v in payload.model_dump().items() if v is not None}
    res = await accounts.update_one({"_id": ObjectId(account_id)}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(404, "not found")
    
    a = await accounts.find_one({"_id": ObjectId(account_id)})
    a["id"] = str(a["_id"])
    a.pop("_id", None)
    return a

@router.delete("/{account_id}")
async def delete_account(account_id: str, user=Depends(verify_token)):
    # Only admin can delete accounts
    if user.get("role") != "admin":
        raise HTTPException(403, "Forbidden: admin only")
    
    res = await accounts.delete_one({"_id": ObjectId(account_id)})
    if res.deleted_count == 0:
        raise HTTPException(404, "not found")
    return {"message": "deleted"}