from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Gateway", version="1.0.0")

# -------------------- CORS --------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- SERVICE URLS --------------------
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
ACCOUNT_SERVICE_URL = os.getenv("ACCOUNT_SERVICE_URL", "http://account-service:8001")
TRANSACTION_SERVICE_URL = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:8002")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8003")

client = httpx.AsyncClient(timeout=30.0)


@app.get("/")
async def root():
    return {"service": "API Gateway", "status": "running"}


# --------------------------------------------------------
#                   AUTH SERVICE
# --------------------------------------------------------
@app.post("/api/auth/register")
async def register(request: Request):
    try:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("host", None)

        response = await client.post(
            f"{AUTH_SERVICE_URL}/api/auth/register",
            content=body, headers=headers
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/auth/login")
async def login(request: Request):
    try:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("host", None)

        response = await client.post(
            f"{AUTH_SERVICE_URL}/api/auth/login",
            content=body, headers=headers
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/auth/me")
async def get_me(request: Request):
    try:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/api/auth/me",
            headers=dict(request.headers)
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


# --------------------------------------------------------
#                   ACCOUNT SERVICE
# --------------------------------------------------------
@app.get("/api/accounts")
async def list_accounts(request: Request):
    try:
        response = await client.get(
            f"{ACCOUNT_SERVICE_URL}/api/accounts",
            headers=dict(request.headers)
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/accounts")
async def create_account(request: Request):
    try:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("host", None)

        response = await client.post(
            f"{ACCOUNT_SERVICE_URL}/api/accounts",
            content=body, headers=headers
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/accounts/{account_id}")
async def get_account(account_id: str, request: Request):
    try:
        response = await client.get(
            f"{ACCOUNT_SERVICE_URL}/api/accounts/{account_id}",
            headers=dict(request.headers)
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: str, request: Request):
    """Delete an account (admin only)"""
    try:
        headers = dict(request.headers)
        headers.pop("host", None)

        response = await client.delete(
            f"{ACCOUNT_SERVICE_URL}/api/accounts/{account_id}",
            headers=headers
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        raise HTTPException(500, str(e))


# --------------------------------------------------------
#                   ADMIN SERVICE
# --------------------------------------------------------
@app.get("/api/admin/stats")
async def admin_stats(request: Request):
    try:
        response = await client.get(
            f"{ACCOUNT_SERVICE_URL}/api/admin/stats",
            headers=dict(request.headers)
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/admin/freeze-account")
async def freeze_account(request: Request):
    try:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("host", None)

        response = await client.post(
            f"{ACCOUNT_SERVICE_URL}/api/admin/freeze-account",
            content=body, headers=headers
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


# --------------------------------------------------------
#                   USERS ENDPOINT
# --------------------------------------------------------
@app.get("/api/users")
async def list_users(request: Request):
    try:
        response = await client.get(
            f"{AUTH_SERVICE_URL}/api/auth/users",
            headers=dict(request.headers)
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


# --------------------------------------------------------
#                   TRANSACTION SERVICE
# --------------------------------------------------------
@app.post("/api/transactions/transfer")
async def transfer(request: Request):
    try:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("host", None)

        response = await client.post(
            f"{TRANSACTION_SERVICE_URL}/api/transactions/transfer",
            content=body, headers=headers
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/transactions/deposit")
async def deposit(request: Request):
    try:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("host", None)

        response = await client.post(
            f"{TRANSACTION_SERVICE_URL}/api/transactions/deposit",
            content=body, headers=headers
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/transactions/withdraw")
async def withdraw(request: Request):
    try:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("host", None)

        response = await client.post(
            f"{TRANSACTION_SERVICE_URL}/api/transactions/withdraw",
            content=body, headers=headers
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/transactions")
async def list_transactions(request: Request):
    try:
        response = await client.get(
            f"{TRANSACTION_SERVICE_URL}/api/transactions",
            headers=dict(request.headers)
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/transactions/{transaction_id}")
async def get_transaction(transaction_id: str, request: Request):
    try:
        response = await client.get(
            f"{TRANSACTION_SERVICE_URL}/api/transactions/{transaction_id}",
            headers=dict(request.headers)
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


# --------------------------------------------------------
#               NOTIFICATION SERVICE
# --------------------------------------------------------
# IMPORTANT: More specific routes MUST come before general routes

@app.get("/api/notifications/unread-count")
async def unread_count(request: Request):
    """Get unread notification count"""
    try:
        response = await client.get(
            f"{NOTIFICATION_SERVICE_URL}/api/notifications/unread-count",
            headers=dict(request.headers)
        )
        return JSONResponse(response.json(), response.status_code)
    except:
        return {"count": 0}


@app.post("/api/notifications/mark-all-read")
async def mark_all_notifications_read(request: Request):
    """Mark all notifications as read"""
    logger.info(f"=== MARK ALL READ REQUEST ===")
    try:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("host", None)

        response = await client.post(
            f"{NOTIFICATION_SERVICE_URL}/api/notifications/mark-all-read",
            content=body,
            headers=headers
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(500, str(e))


@app.patch("/api/notifications/{notification_id}/mark-read")
async def mark_notification_read(notification_id: str, request: Request):
    """Mark a single notification as read"""
    logger.info(f"=== MARK READ REQUEST ===")
    logger.info(f"Notification ID: {notification_id}")
    logger.info(f"Request path: {request.url.path}")
    
    try:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("content-length", None)
        headers.pop("host", None)

        logger.info(f"Forwarding to: {NOTIFICATION_SERVICE_URL}/api/notifications/{notification_id}/mark-read")

        response = await client.patch(
            f"{NOTIFICATION_SERVICE_URL}/api/notifications/{notification_id}/mark-read",
            content=body,
            headers=headers
        )
        
        logger.info(f"Response status: {response.status_code}")
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(500, str(e))


@app.get("/api/notifications")
async def get_notifications(request: Request):
    """Get all notifications"""
    try:
        response = await client.get(
            f"{NOTIFICATION_SERVICE_URL}/api/notifications",
            headers=dict(request.headers)
        )
        return JSONResponse(response.json(), response.status_code)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.on_event("shutdown")
async def shutdown():
    await client.aclose()