from fastapi import APIRouter, HTTPException
from bson import ObjectId
from ..db import accounts, transactions, db
from ..schemas import TransferIn
from ..publisher import publish_notification
import datetime
import uuid
router = APIRouter(prefix="/api/transactions", tags=["transactions"])

@router.post("/transfer")
async def transfer(payload: TransferIn):
    # Basic validation
    a_from = await accounts.find_one({"accountNumber": payload.fromAccount})
    a_to = await accounts.find_one({"accountNumber": payload.toAccount})
    if not a_from or not a_to:
        raise HTTPException(404, "Account not found")
    if a_from.get("status","active") != "active":
        raise HTTPException(400, "Sender account not active")
    if a_from.get("balance",0) < payload.amount:
        raise HTTPException(400, "Insufficient funds")

    # Use MongoDB transaction (requires replica sets + mongos)
    async with await db.client.start_session() as s:
        async with s.start_transaction():
            # decrement sender
            await accounts.update_one({"accountNumber": payload.fromAccount},
                                      {"$inc": {"balance": -payload.amount}}, session=s)
            # increment receiver
            await accounts.update_one({"accountNumber": payload.toAccount},
                                      {"$inc": {"balance": payload.amount}}, session=s)
            # create transaction record
            tx = {
                "txId": f"TXN-{uuid.uuid4().hex[:12]}",
                "fromAccount": payload.fromAccount,
                "toAccount": payload.toAccount,
                "amount": payload.amount,
                "currency": payload.currency,
                "status": "SUCCESS",
                "createdAt": datetime.datetime.utcnow()
            }
            res = await transactions.insert_one(tx, session=s)
    # publish notification asynchronously (fire-and-forget)
    publish_notification({
        "userId": str(a_from.get("userId")),
        "type": "TRANSACTION",
        "payload": {"message": f"Transfer of {payload.amount} {payload.currency} to {payload.toAccount}", "txId": tx["txId"]},
        "createdAt": datetime.datetime.utcnow().isoformat()
    })
    return {"status":"success","txId": tx["txId"]}
