from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .routes import notifications
from .cache import cache
import os

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])

app = FastAPI(title="Notification Service")

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    print("✓ Notification Service started")
    print(f"  - MongoDB: {os.getenv('MONGO_URI', 'Not configured')}")
    print(f"  - Redis Cache: {'✓ Connected' if cache.is_connected() else '✗ Disconnected'}")
    print(f"  - RabbitMQ: {os.getenv('RABBITMQ_HOST', 'Not configured')}")

# Health check
@app.get("/")
@limiter.exempt
def root():
    return {
        "message": "Notification service running 📬",
        "status": "healthy",
        "redis": cache.is_connected()
    }

# Include routers
app.include_router(notifications.router)