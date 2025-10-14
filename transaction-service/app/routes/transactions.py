from fastapi import APIRouter, HTTPException, Query, Depends
from bson import ObjectId
from ..db import accounts, transactions, db
from ..schemas import TransferIn, TransactionOut
from ..publisher import publish_notification, publish_error
from ..auth import verify_token
import datetime
import uuid

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

@router.post("/transfer")
async def transfer(payload: TransferIn, user=Depends(verify_token)):
    # Basic validation
    a_from = await accounts.find_one({"accountNumber": payload.fromAccount})
    a_to = await accounts.find_one({"accountNumber": payload.toAccount})
    
    if not a_from or not a_to:
        raise HTTPException(404, "Account not found")
    
    # Check if user owns the fromAccount (unless admin)
    if user.get("role") != "admin" and a_from.get("userId") != user.get("user_id"):
        raise HTTPException(403, "Forbidden: can only transfer from your own account")
    
    if a_from.get("status", "active") != "active":
        raise HTTPException(400, "Sender account not active")
    
    if a_to.get("status", "active") != "active":
        raise HTTPException(400, "Receiver account not active")
    
    if a_from.get("balance", 0) < payload.amount:
        raise HTTPException(400, "Insufficient funds")

    tx_id = f"TXN-{uuid.uuid4().hex[:12]}"
    
    try:
        # Use MongoDB transaction (requires replica sets + mongos)
        async with await db.client.start_session() as s:
            async with s.start_transaction():
                # Decrement sender
                await accounts.update_one(
                    {"accountNumber": payload.fromAccount},
                    {"$inc": {"balance": -payload.amount}}, 
                    session=s
                )
                # Increment receiver
                await accounts.update_one(
                    {"accountNumber": payload.toAccount},
                    {"$inc": {"balance": payload.amount}}, 
                    session=s
                )
                # Create transaction record
                tx = {
                    "txId": tx_id,
                    "fromAccount": payload.fromAccount,
                    "toAccount": payload.toAccount,
                    "amount": payload.amount,
                    "currency": payload.currency,
                    "status": "SUCCESS",
                    "createdAt": datetime.datetime.utcnow(),
                    "retry_count": 0
                }
                await transactions.insert_one(tx, session=s)
        
        # Publish notifications asynchronously (fire-and-forget)
        try:
            publish_notification({
                "userId": str(a_from.get("userId")),
                "type": "TRANSACTION_SENT",
                "payload": {
                    "message": f"Transfer of {payload.amount} {payload.currency} to {payload.toAccount}",
                    "txId": tx_id,
                    "amount": payload.amount
                },
                "createdAt": datetime.datetime.utcnow().isoformat()
            })
            
            publish_notification({
                "userId": str(a_to.get("userId")),
                "type": "TRANSACTION_RECEIVED",
                "payload": {
                    "message": f"Received {payload.amount} {payload.currency} from {payload.fromAccount}",
                    "txId": tx_id,
                    "amount": payload.amount
                },
                "createdAt": datetime.datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"Warning: Failed to publish notification: {e}")
        
        return {"status": "success", "txId": tx_id}
    
    except Exception as e:
        error_msg = {
            "txId": tx_id,
            "fromAccount": payload.fromAccount,
            "toAccount": payload.toAccount,
            "amount": payload.amount,
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "retry_count": 0
        }
        try:
            publish_error(error_msg)
        except:
            pass
        raise HTTPException(400, f"Transfer failed: {str(e)}")

@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    user=Depends(verify_token),
    fromAccount: str | None = None,
    toAccount: str | None = None,
    limit: int = Query(50, le=200)
):
    q = {}
    
    # Non-admin users can only see their own transactions
    if user.get("role") != "admin":
        user_accounts = []
        async for acc in accounts.find({"userId": user.get("user_id")}):
            user_accounts.append(acc.get("accountNumber"))
        
        if not user_accounts:
            return []
        
        q["$or"] = [
            {"fromAccount": {"$in": user_accounts}},
            {"toAccount": {"$in": user_accounts}}
        ]
    
    # Apply filters
    if fromAccount:
        q["fromAccount"] = fromAccount
    if toAccount:
        q["toAccount"] = toAccount
    
    cur = transactions.find(q).sort("createdAt", -1).limit(limit)
    result = []
    async for tx in cur:
        tx["id"] = str(tx["_id"])
        tx.pop("_id", None)
        result.append(tx)
    
    return result

@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction(transaction_id: str, user=Depends(verify_token)):
    try:
        tx = await transactions.find_one({"txId": transaction_id})
    except:
        raise HTTPException(400, "Invalid transaction ID")
    
    if not tx:
        raise HTTPException(404, "Transaction not found")
    
    # Check authorization - user must be involved in the transaction
    if user.get("role") != "admin":
        user_accounts = []
        async for acc in accounts.find({"userId": user.get("user_id")}):
            user_accounts.append(acc.get("accountNumber"))
        
        if tx.get("fromAccount") not in user_accounts and tx.get("toAccount") not in user_accounts:
            raise HTTPException(403, "Forbidden")
    
    tx["id"] = str(tx["_id"])
    tx.pop("_id", None)
    return tx