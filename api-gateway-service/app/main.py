from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(title="API Gateway")

# Service URLs
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
ACCOUNT_SERVICE_URL = os.getenv("ACCOUNT_SERVICE_URL", "http://account-service:8001")
TRANSACTION_SERVICE_URL = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:8002")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8003")

# Service routing map
ROUTES = {
    "/api/auth": AUTH_SERVICE_URL,
    "/api/accounts": ACCOUNT_SERVICE_URL,
    "/api/transactions": TRANSACTION_SERVICE_URL,
    "/api/notifications": NOTIFICATION_SERVICE_URL,
    "/api/admin": ACCOUNT_SERVICE_URL,  # Admin endpoints on account service
}

@app.get("/")
def root():
    return {
        "message": "API Gateway running",
        "version": "1.0",
        "services": {
            "auth": AUTH_SERVICE_URL,
            "accounts": ACCOUNT_SERVICE_URL,
            "transactions": TRANSACTION_SERVICE_URL,
            "notifications": NOTIFICATION_SERVICE_URL
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "gateway": "running"
    }

async def route_request(request: Request):
    """Generic request router"""
    path = request.url.path
    
    # Find matching service
    target_service = None
    for route_prefix, service_url in ROUTES.items():
        if path.startswith(route_prefix):
            target_service = service_url
            break
    
    if not target_service:
        raise HTTPException(404, "Route not found")
    
    # Prepare request
    method = request.method
    headers = dict(request.headers)
    
    # Remove host header to avoid conflicts
    headers.pop("host", None)
    
    # Construct target URL
    target_path = path
    if request.url.query:
        target_path = f"{path}?{request.url.query}"
    
    target_url = f"{target_service}{target_path}"
    
    try:
        body = await request.body()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                target_url,
                headers=headers,
                content=body if body else None
            )
            
            return JSONResponse(
                status_code=response.status_code,
                content=response.json() if response.text else {}
            )
    except httpx.ConnectError:
        raise HTTPException(503, f"Service unavailable: {target_service}")
    except httpx.TimeoutException:
        raise HTTPException(504, "Service timeout")
    except Exception as e:
        raise HTTPException(500, f"Gateway error: {str(e)}")

# Route all HTTP methods
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def gateway_route(request: Request):
    return await route_request(request)