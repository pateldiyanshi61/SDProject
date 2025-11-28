from fastapi import APIRouter, HTTPException, Query, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from bson import ObjectId
from ..db import accounts, transactions, db
from ..schemas import TransferIn, TransactionOut, DepositIn, WithdrawIn
from ..publisher import publish_notification, publish_error
from ..auth import verify_token
from ..cache import cache, invalidate_cache
import datetime
import uuid

router = APIRouter(
    prefix="/api/transactions",
    tags=["transactions"]
)

limiter = Limiter(key_func=get_remote_address)


# ============================
#        DEPOSIT MONEY
# ============================
@router.post("/deposit")
@limiter.limit("10/minute")
async def deposit(request: Request, payload: DepositIn, user=Depends(verify_token)):
    """Deposit money into user's own account (or any account for admin)"""
    
    print("=" * 60)
    print("DEPOSIT REQUEST DEBUG INFO")
    print("=" * 60)
    print(f"User from JWT: {user}")
    print(f"To account: {payload.accountNumber}")
    print(f"Amount: {payload.amount}")

    cache_key = f"account:number:{payload.accountNumber}"
    
    account = cache.get(cache_key)
    if not account:
        account = await accounts.find_one({"accountNumber": payload.accountNumber})
        if account:
            cache.set(cache_key, dict(account), ttl=300)

    if not account:
        print(f"ERROR: Account not found")
        raise HTTPException(404, "Account not found")

    print(f"Account Data: {account}")

    account_user_id = str(account.get("userId", ""))
    token_user_id = str(user.get("user_id", ""))
    user_role = user.get("role", "")
    
    print(f"Account userId: '{account_user_id}'")
    print(f"Token userId: '{token_user_id}'")
    print(f"User role: '{user_role}'")

    # User can only deposit to their own account (except admin)
    if user_role != "admin" and account_user_id != token_user_id:
        error_msg = (
            f"Forbidden: can only deposit to your own account. "
            f"Account '{payload.accountNumber}' belongs to user '{account_user_id}', "
            f"but you are user '{token_user_id}'"
        )
        print(f"ERROR: {error_msg}")
        raise HTTPException(403, error_msg)
    
    # Log if admin is depositing to another user's account
    if user_role == "admin" and account_user_id != token_user_id:
        print(f"⚠️ ADMIN DEPOSIT: Admin {token_user_id} depositing to user {account_user_id}'s account")

    if account.get("status") != "active":
        print(f"ERROR: Account status is {account.get('status')}")
        raise HTTPException(400, "Account not active")

    if payload.amount <= 0:
        print(f"ERROR: Invalid amount: {payload.amount}")
        raise HTTPException(400, "Amount must be greater than 0")

    tx_id = f"DEP-{uuid.uuid4().hex[:12]}"
    print(f"Generated transaction ID: {tx_id}")

    try:
        async with await db.client.start_session() as session:
            async with session.start_transaction():
                result = await accounts.update_one(
                    {"accountNumber": payload.accountNumber},
                    {"$inc": {"balance": payload.amount}},
                    session=session
                )

                if result.modified_count == 0:
                    raise Exception("Failed to update account balance")

                tx_doc = {
                    "txId": tx_id,
                    "fromAccount": "DEPOSIT",
                    "toAccount": payload.accountNumber,
                    "amount": payload.amount,
                    "currency": payload.currency,
                    "status": "SUCCESS",
                    "type": "DEPOSIT",
                    "description": payload.description or "Account deposit",
                    "createdAt": datetime.datetime.utcnow(),
                }

                await transactions.insert_one(tx_doc, session=session)

        invalidate_cache(f"account:number:{payload.accountNumber}")
        cache.set(f"transaction:id:{tx_id}", tx_doc, ttl=600)

        try:
            publish_notification({
                "userId": str(account["userId"]),
                "type": "DEPOSIT_SUCCESS",
                "payload": {
                    "message": f"Successfully deposited {payload.amount} {payload.currency} to account {payload.accountNumber}",
                    "txId": tx_id,
                    "amount": payload.amount,
                    "currency": payload.currency
                },
                "createdAt": datetime.datetime.utcnow().isoformat(),
                "priority": "normal"
            })
        except Exception as e:
            print(f"Notification failure: {e}")

        print("✓ Deposit successful!")
        print("=" * 60)
        
        return {
            "status": "success",
            "txId": tx_id,
            "message": f"Successfully deposited {payload.amount} {payload.currency}",
            "newBalance": account.get("balance", 0) + payload.amount
        }

    except Exception as e:
        print(f"ERROR: Deposit failed - {str(e)}")
        print("=" * 60)
        
        try:
            publish_error({
                "txId": tx_id,
                "error": str(e),
                "type": "DEPOSIT_FAILED",
                "timestamp": datetime.datetime.utcnow().isoformat(),
            })
        except:
            pass
            
        raise HTTPException(400, f"Deposit failed: {str(e)}")


# ============================
#        WITHDRAW MONEY
# ============================
@router.post("/withdraw")
@limiter.limit("10/minute")
async def withdraw(request: Request, payload: WithdrawIn, user=Depends(verify_token)):
    """Withdraw money from user's own account (or any account for admin)"""
    
    print("=" * 60)
    print("WITHDRAW REQUEST DEBUG INFO")
    print("=" * 60)
    print(f"User from JWT: {user}")
    print(f"From account: {payload.accountNumber}")
    print(f"Amount: {payload.amount}")

    cache_key = f"account:number:{payload.accountNumber}"
    
    account = cache.get(cache_key)
    if not account:
        account = await accounts.find_one({"accountNumber": payload.accountNumber})
        if account:
            cache.set(cache_key, dict(account), ttl=300)

    if not account:
        print(f"ERROR: Account not found")
        raise HTTPException(404, "Account not found")

    print(f"Account Data: {account}")

    account_user_id = str(account.get("userId", ""))
    token_user_id = str(user.get("user_id", ""))
    user_role = user.get("role", "")
    
    print(f"Account userId: '{account_user_id}'")
    print(f"Token userId: '{token_user_id}'")
    print(f"User role: '{user_role}'")

    # User can only withdraw from their own account (except admin)
    if user_role != "admin" and account_user_id != token_user_id:
        error_msg = (
            f"Forbidden: can only withdraw from your own account. "
            f"Account '{payload.accountNumber}' belongs to user '{account_user_id}', "
            f"but you are user '{token_user_id}'"
        )
        print(f"ERROR: {error_msg}")
        raise HTTPException(403, error_msg)
    
    # Log if admin is withdrawing from another user's account
    if user_role == "admin" and account_user_id != token_user_id:
        print(f"⚠️ ADMIN WITHDRAW: Admin {token_user_id} withdrawing from user {account_user_id}'s account")

    if account.get("status") != "active":
        print(f"ERROR: Account status is {account.get('status')}")
        raise HTTPException(400, "Account not active")

    if payload.amount <= 0:
        print(f"ERROR: Invalid amount: {payload.amount}")
        raise HTTPException(400, "Amount must be greater than 0")

    # Check sufficient balance
    if account.get("balance", 0) < payload.amount:
        print(f"ERROR: Insufficient funds - balance: {account.get('balance', 0)}, required: {payload.amount}")
        raise HTTPException(400, "Insufficient funds")

    tx_id = f"WDR-{uuid.uuid4().hex[:12]}"
    print(f"Generated transaction ID: {tx_id}")

    try:
        async with await db.client.start_session() as session:
            async with session.start_transaction():
                result = await accounts.update_one(
                    {"accountNumber": payload.accountNumber},
                    {"$inc": {"balance": -payload.amount}},
                    session=session
                )

                if result.modified_count == 0:
                    raise Exception("Failed to update account balance")

                tx_doc = {
                    "txId": tx_id,
                    "fromAccount": payload.accountNumber,
                    "toAccount": "WITHDRAW",  # Special marker for withdrawals
                    "amount": payload.amount,
                    "currency": payload.currency,
                    "status": "SUCCESS",
                    "type": "WITHDRAW",
                    "description": payload.description or "Account withdrawal",
                    "createdAt": datetime.datetime.utcnow(),
                }

                await transactions.insert_one(tx_doc, session=session)

        invalidate_cache(f"account:number:{payload.accountNumber}")
        cache.set(f"transaction:id:{tx_id}", tx_doc, ttl=600)

        try:
            publish_notification({
                "userId": str(account["userId"]),
                "type": "WITHDRAW_SUCCESS",
                "payload": {
                    "message": f"Successfully withdrew {payload.amount} {payload.currency} from account {payload.accountNumber}",
                    "txId": tx_id,
                    "amount": payload.amount,
                    "currency": payload.currency
                },
                "createdAt": datetime.datetime.utcnow().isoformat(),
                "priority": "normal"
            })
        except Exception as e:
            print(f"Notification failure: {e}")

        print("✓ Withdrawal successful!")
        print("=" * 60)
        
        return {
            "status": "success",
            "txId": tx_id,
            "message": f"Successfully withdrew {payload.amount} {payload.currency}",
            "newBalance": account.get("balance", 0) - payload.amount
        }

    except Exception as e:
        print(f"ERROR: Withdrawal failed - {str(e)}")
        print("=" * 60)
        
        try:
            publish_error({
                "txId": tx_id,
                "error": str(e),
                "type": "WITHDRAW_FAILED",
                "timestamp": datetime.datetime.utcnow().isoformat(),
            })
        except:
            pass
            
        raise HTTPException(400, f"Withdrawal failed: {str(e)}")


# ============================
#        TRANSFER MONEY
# ============================
@router.post("/transfer")
@limiter.limit("30/minute")
async def transfer(request: Request, payload: TransferIn, user=Depends(verify_token)):

    print("=" * 60)
    print("TRANSFER REQUEST DEBUG INFO")
    print("=" * 60)
    print(f"User from JWT: {user}")
    print(f"From account: {payload.fromAccount}")
    print(f"To account: {payload.toAccount}")
    print(f"Amount: {payload.amount}")

    from_cache_key = f"account:number:{payload.fromAccount}"
    to_cache_key = f"account:number:{payload.toAccount}"

    a_from = cache.get(from_cache_key)
    a_to = cache.get(to_cache_key)

    if not a_from:
        a_from = await accounts.find_one({"accountNumber": payload.fromAccount})
        if a_from:
            cache.set(from_cache_key, dict(a_from), ttl=300)

    if not a_to:
        a_to = await accounts.find_one({"accountNumber": payload.toAccount})
        if a_to:
            cache.set(to_cache_key, dict(a_to), ttl=300)

    if not a_from or not a_to:
        print(f"ERROR: Account not found - from: {a_from is not None}, to: {a_to is not None}")
        raise HTTPException(404, "Account not found")

    print(f"From Account Data: {a_from}")
    print(f"To Account Data: {a_to}")

    from_user_id = str(a_from.get("userId", ""))
    token_user_id = str(user.get("user_id", ""))
    user_role = user.get("role", "")
    
    print(f"Account userId: '{from_user_id}' (type: {type(a_from.get('userId'))})")
    print(f"Token userId: '{token_user_id}' (type: {type(user.get('user_id'))})")
    print(f"User role: '{user_role}'")
    print(f"Match: {from_user_id == token_user_id}")

    if user_role != "admin" and from_user_id != token_user_id:
        error_msg = (
            f"Forbidden: can only transfer from your own account. "
            f"Account '{payload.fromAccount}' belongs to user '{from_user_id}', "
            f"but you are user '{token_user_id}'"
        )
        print(f"ERROR: {error_msg}")
        raise HTTPException(403, error_msg)

    if a_from.get("status") != "active":
        print(f"ERROR: Sender account status is {a_from.get('status')}")
        raise HTTPException(400, "Sender account not active")

    if a_to.get("status") != "active":
        print(f"ERROR: Receiver account status is {a_to.get('status')}")
        raise HTTPException(400, "Receiver account not active")

    if a_from.get("balance", 0) < payload.amount:
        print(f"ERROR: Insufficient funds - balance: {a_from.get('balance', 0)}, required: {payload.amount}")
        raise HTTPException(400, "Insufficient funds")

    tx_id = f"TXN-{uuid.uuid4().hex[:12]}"
    print(f"Generated transaction ID: {tx_id}")

    try:
        async with await db.client.start_session() as session:
            async with session.start_transaction():

                await accounts.update_one(
                    {"accountNumber": payload.fromAccount},
                    {"$inc": {"balance": -payload.amount}},
                    session=session
                )

                await accounts.update_one(
                    {"accountNumber": payload.toAccount},
                    {"$inc": {"balance": payload.amount}},
                    session=session
                )

                tx_doc = {
                    "txId": tx_id,
                    "fromAccount": payload.fromAccount,
                    "toAccount": payload.toAccount,
                    "amount": payload.amount,
                    "currency": payload.currency,
                    "status": "SUCCESS",
                    "type": "TRANSFER",
                    "createdAt": datetime.datetime.utcnow(),
                }

                await transactions.insert_one(tx_doc, session=session)

        invalidate_cache(f"account:number:{payload.fromAccount}")
        invalidate_cache(f"account:number:{payload.toAccount}")
        cache.set(f"transaction:id:{tx_id}", tx_doc, ttl=600)

        try:
            publish_notification({
                "userId": str(a_from["userId"]),
                "type": "TRANSACTION_SENT",
                "payload": {
                    "message": f"Sent {payload.amount} {payload.currency} to {payload.toAccount}",
                    "txId": tx_id
                },
                "createdAt": datetime.datetime.utcnow().isoformat()
            })

            publish_notification({
                "userId": str(a_to["userId"]),
                "type": "TRANSACTION_RECEIVED",
                "payload": {
                    "message": f"Received {payload.amount} {payload.currency} from {payload.fromAccount}",
                    "txId": tx_id
                },
                "createdAt": datetime.datetime.utcnow().isoformat()
            })

        except Exception as e:
            print(f"Notification failure: {e}")

        print("✓ Transfer successful!")
        print("=" * 60)
        return {"status": "success", "txId": tx_id}

    except Exception as e:
        print(f"ERROR: Transfer failed - {str(e)}")
        print("=" * 60)
        publish_error({
            "txId": tx_id,
            "error": str(e),
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })
        raise HTTPException(400, f"Transfer failed: {str(e)}")


# ============================
#    LIST MY TRANSACTIONS
# ============================
@router.get("", response_model=list[TransactionOut])
@limiter.limit("60/minute")
async def list_transactions(
    request: Request,
    user=Depends(verify_token),
    fromAccount: str | None = None,
    toAccount: str | None = None,
    limit: int = Query(50, le=200)
):
    query = {}

    if user.get("role") != "admin":
        user_acc_nums = []
        async for acc in accounts.find({"userId": user["user_id"]}):
            user_acc_nums.append(acc["accountNumber"])

        if not user_acc_nums:
            return []

        query["$or"] = [
            {"fromAccount": {"$in": user_acc_nums}},
            {"toAccount": {"$in": user_acc_nums}},
        ]

    if fromAccount:
        query["fromAccount"] = fromAccount

    if toAccount:
        query["toAccount"] = toAccount

    cur = transactions.find(query).sort("createdAt", -1).limit(limit)
    result = []
    async for tx in cur:
        tx["id"] = str(tx["_id"])
        tx.pop("_id", None)
        result.append(tx)

    return result


# ============================
#    GET TRANSACTION BY ID
# ============================
@router.get("/{transaction_id}", response_model=TransactionOut)
@limiter.limit("60/minute")
async def get_transaction(request: Request, transaction_id: str, user=Depends(verify_token)):

    tx = await transactions.find_one({"txId": transaction_id})
    if not tx:
        raise HTTPException(404, "Transaction not found")

    if user.get("role") != "admin":
        user_accounts = []
        async for acc in accounts.find({"userId": user["user_id"]}):
            user_accounts.append(acc["accountNumber"])

        if tx["fromAccount"] not in user_accounts and tx["toAccount"] not in user_accounts:
            raise HTTPException(403, "Forbidden")

    tx["id"] = str(tx["_id"])
    tx.pop("_id", None)

    return tx