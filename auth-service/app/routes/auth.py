from fastapi import APIRouter, HTTPException, Header, Depends, Request
from passlib.context import CryptContext
from slowapi import Limiter
from slowapi.util import get_remote_address
from bson import ObjectId
from ..db import users
from ..schemas import UserCreate, UserOut, LoginIn
from ..services.jwt_utils import create_access_token, decode_token
from ..cache import cache, invalidate_cache
import hashlib

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

# --- helper functions ---

def safe_password_hash(password: str) -> str:
    """Hashes password safely. Handles >72 byte bcrypt limit by pre-hashing using SHA-256."""
    if len(password.encode()) > 72:
        password = hashlib.sha256(password.encode()).hexdigest()
    return pwd.hash(password)

def safe_password_verify(password: str, hashed: str) -> bool:
    """Verifies password using same pre-hash logic."""
    if len(password.encode()) > 72:
        password = hashlib.sha256(password.encode()).hexdigest()
    return pwd.verify(password, hashed)


# --- token verification dependency ---
async def get_current_user(authorization: str = Header(...)):
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid auth scheme")
        
        data = decode_token(token)
        
        # Try to get user from cache
        user_id = data.get("user_id")
        if user_id:
            cache_key = f"user:id:{user_id}"
            cached_user = cache.get(cache_key)
            if cached_user:
                return cached_user
        
        # If not in cache, return decoded token data
        return data
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


# --- routes ---

@router.post("/register", response_model=UserOut)
@limiter.limit("10/minute")  # Strict rate limiting for registration
async def register(request: Request, payload: UserCreate):
    print(await request.json())
    
    # Check cache first
    cache_key = f"user:email:{payload.email}"
    if cache.get(cache_key):
        raise HTTPException(status_code=400, detail="Email already exists")

    # Check database
    if await users.find_one({"email": payload.email}):
        # Cache the existence check to prevent repeated DB queries
        cache.set(cache_key, {"exists": True}, ttl=600)
        raise HTTPException(status_code=400, detail="Email already exists")

    # Hash password safely
    pw_hash = safe_password_hash(payload.password)

    res = await users.insert_one({
        "email": payload.email,
        "passwordHash": pw_hash,
        "role": payload.role,
        "profile": payload.profile or {},
        "createdAt": None
    })

    u = await users.find_one({"_id": res.inserted_id})
    
    user_data = {
        "id": str(u["_id"]),
        "email": u["email"],
        "role": u.get("role", "user"),
        "profile": u.get("profile", {})
    }
    
    # Cache user data
    cache.set(f"user:id:{user_data['id']}", user_data, ttl=1800)
    cache.set(cache_key, {"exists": True}, ttl=600)
    
    return user_data


@router.post("/login")
@limiter.limit("10/minute")  # Prevent brute force attacks
async def login(request: Request, payload: LoginIn):
    # Try cache first (stores user info after successful login)
    cache_key = f"user:login:{payload.email}"
    cached_user = cache.get(cache_key)
    
    # Always verify from DB for security
    u = await users.find_one({"email": payload.email})
    if not u or not safe_password_verify(payload.password, u["passwordHash"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token_data = {
        "user_id": str(u["_id"]),
        "role": u.get("role", "user"),
        "email": u["email"]
    }
    
    # Cache user info (without password hash) for faster subsequent requests
    cache.set(cache_key, token_data, ttl=1800)
    cache.set(f"user:id:{token_data['user_id']}", token_data, ttl=1800)

    token = create_access_token(token_data)

    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
@limiter.limit("60/minute")
async def me(request: Request, user=Depends(get_current_user)):
    """Get current user info - REQUIRES request parameter for rate limiting"""
    return user


@router.get("/users")
@limiter.limit("30/minute")
async def list_users(request: Request, user=Depends(get_current_user)):
    """List all users - admin only with caching"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: admin only")
    
    # Try cache first
    cache_key = "users:all:list"
    cached_users = cache.get(cache_key)
    if cached_users:
        return cached_users
    
    # Fetch from DB - FIXED: use 'users' not 'users_collection'
    cur = users.find({})
    result = []
    async for u in cur:
        result.append({
            "id": str(u["_id"]),
            "email": u["email"],
            "role": u.get("role", "user"),
            "profile": u.get("profile", {})
        })
    
    # Cache the result
    cache.set(cache_key, result, ttl=600)
    
    return result


@router.post("/logout")
@limiter.limit("30/minute")
async def logout(request: Request, user=Depends(get_current_user)):
    """Logout - invalidate user cache"""
    user_id = user.get("user_id")
    if user_id:
        # Invalidate all user-related cache
        invalidate_cache(f"user:id:{user_id}")
        invalidate_cache(f"user:login:{user.get('email', '*')}")
    
    return {"message": "Logged out successfully"}