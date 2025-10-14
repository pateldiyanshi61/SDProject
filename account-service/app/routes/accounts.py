from fastapi import APIRouter, HTTPException, Query, Depends, Header
from bson import ObjectId
from ..db import accounts
from ..schemas import AccountCreate, AccountOut, AccountUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

@router.post("", response_model=AccountOut)
async def create_account(payload: AccountCreate):
    if await accounts.find_one({"accountNumber": payload.accountNumber}):
        raise HTTPException(400, "accountNumber exists")
    res = await accounts.insert_one(payload.model_dump())
    acc = await accounts.find_one({"_id": res.inserted_id})
    return {"id": str(acc["_id"]), **{k:v for k,v in acc.items() if k!="_id"}}

@router.get("", response_model=list[AccountOut])
async def list_accounts(user_id: str | None = None):
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
async def get_account(account_id: str):
    a = await accounts.find_one({"_id": ObjectId(account_id)})
    if not a:
        raise HTTPException(404, "not found")
    a["id"] = str(a["_id"]); a.pop("_id", None)
    return a

@router.put("/{account_id}", response_model=AccountOut)
async def update_account(account_id: str, payload: AccountUpdate):
    upd = {k:v for k,v in payload.model_dump().items() if v is not None}
    res = await accounts.update_one({"_id": ObjectId(account_id)}, {"$set": upd})
    if res.matched_count==0:
        raise HTTPException(404, "not found")
    a = await accounts.find_one({"_id": ObjectId(account_id)})
    a["id"] = str(a["_id"]); a.pop("_id", None)
    return a

@router.delete("/{account_id}")
async def delete_account(account_id: str):
    res = await accounts.delete_one({"_id": ObjectId(account_id)})
    if res.deleted_count==0:
        raise HTTPException(404,"not found")
    return {"message":"deleted"}
