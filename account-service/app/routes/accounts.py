from fastapi import APIRouter, HTTPException, Query, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from bson import ObjectId
from ..db import accounts
from ..schemas import AccountCreate, AccountOut, AccountUpdate
from ..auth import verify_token
from ..cache import cache, invalidate_cache

router = APIRouter(prefix="/api/accounts", tags=["accounts"])
limiter = Limiter(key_func=get_remote_address)

@router.post("", response_model=AccountOut)
@limiter.limit("10/minute")
async def create_account(request: Request, payload: AccountCreate, user=Depends(verify_token)):
    # Only admin can create accounts for others
    if user.get("role") != "admin" and payload.userId != user.get("user_id"):
        raise HTTPException(403, "Forbidden: cannot create account for another user")
    
    # Check cache for duplicate account number
    cache_key = f"account:number:{payload.accountNumber}"
    if cache.get(cache_key):
        raise HTTPException(400, "accountNumber exists")
    
    if await accounts.find_one({"accountNumber": payload.accountNumber}):
        cache.set(cache_key, {"exists": True})
        raise HTTPException(400, "accountNumber exists")
    
    res = await accounts.insert_one(payload.model_dump())
    acc = await accounts.find_one({"_id": res.inserted_id})
    
    account_data = {"id": str(acc["_id"]), **{k:v for k,v in acc.items() if k!="_id"}}
    
    # Cache the new account
    cache.set(f"account:id:{account_data['id']}", account_data)
    cache.set(cache_key, account_data)
    
    # Invalidate user's account list cache
    invalidate_cache(f"accounts:user:{payload.userId}:*")
    
    return account_data


@router.get("", response_model=list[AccountOut])
@limiter.limit("60/minute")
async def list_accounts(request: Request, user_id: str | None = None, user=Depends(verify_token)):
    # Admin can see all accounts, users can only see their own
    if user.get("role") != "admin":
        user_id = user.get("user_id")
    
    # Try cache first
    cache_key = f"accounts:user:{user_id}:list" if user_id else "accounts:all:list"
    cached_accounts = cache.get(cache_key)
    if cached_accounts:
        return cached_accounts
    
    q = {}
    if user_id:
        q["userId"] = user_id
    
    cur = accounts.find(q)
    result = []
    async for a in cur:
        a["id"] = str(a["_id"])
        a.pop("_id", None)
        result.append(a)
    
    # Cache the result
    cache.set(cache_key, result)
    
    return result


@router.get("/{account_id}", response_model=AccountOut)
@limiter.limit("60/minute")
async def get_account(request: Request, account_id: str, user=Depends(verify_token)):
    # Try cache first
    cache_key = f"account:id:{account_id}"
    cached_account = cache.get(cache_key)
    
    if cached_account:
        # Still check authorization
        if user.get("role") != "admin" and cached_account.get("userId") != user.get("user_id"):
            raise HTTPException(403, "Forbidden")
        return cached_account
    
    # Fetch from DB
    a = await accounts.find_one({"_id": ObjectId(account_id)})
    if not a:
        raise HTTPException(404, "not found")
    
    # Check authorization
    if user.get("role") != "admin" and a.get("userId") != user.get("user_id"):
        raise HTTPException(403, "Forbidden")
    
    account_data = {"id": str(a["_id"]), **{k:v for k,v in a.items() if k!="_id"}}
    
    # Cache it
    cache.set(cache_key, account_data)
    
    return account_data


@router.get("/{account_id}/balance")
@limiter.limit("60/minute")
async def get_balance(request: Request, account_id: str, user=Depends(verify_token)):
    # Try cache for balance (shorter TTL since balances change frequently)
    cache_key = f"balance:account:{account_id}"
    cached_balance = cache.get(cache_key)
    
    if cached_balance:
        # Verify ownership
        if user.get("role") != "admin" and cached_balance.get("userId") != user.get("user_id"):
            raise HTTPException(403, "Forbidden")
        return cached_balance
    
    # Fetch from DB
    a = await accounts.find_one({"_id": ObjectId(account_id)})
    if not a:
        raise HTTPException(404, "not found")
    
    # Check authorization
    if user.get("role") != "admin" and a.get("userId") != user.get("user_id"):
        raise HTTPException(403, "Forbidden")
    
    balance_data = {
        "accountId": str(a["_id"]),
        "accountNumber": a.get("accountNumber"),
        "balance": a.get("balance", 0.0),
        "currency": a.get("currency", "INR"),
        "userId": a.get("userId")
    }
    
    # Cache with shorter TTL (5 minutes)
    cache.set(cache_key, balance_data)
    
    # Remove userId from response
    balance_data.pop("userId")
    return balance_data


@router.put("/{account_id}", response_model=AccountOut)
@limiter.limit("30/minute")
async def update_account(request: Request, account_id: str, payload: AccountUpdate, user=Depends(verify_token)):
    # Only admin can update accounts
    if user.get("role") != "admin":
        raise HTTPException(403, "Forbidden: admin only")
    
    upd = {k:v for k,v in payload.model_dump().items() if v is not None}
    res = await accounts.update_one({"_id": ObjectId(account_id)}, {"$set": upd})
    if res.matched_count == 0:
        raise HTTPException(404, "not found")
    
    a = await accounts.find_one({"_id": ObjectId(account_id)})
    account_data = {"id": str(a["_id"]), **{k:v for k,v in a.items() if k!="_id"}}
    
    # Invalidate caches
    invalidate_cache(f"account:id:{account_id}")
    invalidate_cache(f"balance:account:{account_id}")
    invalidate_cache(f"accounts:user:{a.get('userId')}:*")
    
    return account_data


@router.delete("/{account_id}")
@limiter.limit("20/minute")
async def delete_account(request: Request, account_id: str, user=Depends(verify_token)):
    # Only admin can delete accounts
    if user.get("role") != "admin":
        raise HTTPException(403, "Forbidden: admin only")
    
    # Get account before deletion for cache invalidation
    a = await accounts.find_one({"_id": ObjectId(account_id)})
    if not a:
        raise HTTPException(404, "not found")
    
    res = await accounts.delete_one({"_id": ObjectId(account_id)})
    if res.deleted_count == 0:
        raise HTTPException(404, "not found")
    
    # Invalidate all related caches
    invalidate_cache(f"account:id:{account_id}")
    invalidate_cache(f"balance:account:{account_id}")
    invalidate_cache(f"accounts:user:{a.get('userId')}:*")
    invalidate_cache("accounts:all:*")
    
    return {"message": "deleted"}