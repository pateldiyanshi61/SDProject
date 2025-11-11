from fastapi import APIRouter, HTTPException, Header, Depends, Request
from passlib.context import CryptContext
from bson import ObjectId
from ..db import users
from ..schemas import UserCreate, UserOut, LoginIn
from ..services.jwt_utils import create_access_token, decode_token
import hashlib

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/api/auth", tags=["auth"])

# --- helper functions ---

def safe_password_hash(password: str) -> str:
    """
    Hashes password safely. Handles >72 byte bcrypt limit by pre-hashing using SHA-256.
    """
    # bcrypt only supports 72 bytes → pre-hash to ensure consistent length
    if len(password.encode()) > 72:
        password = hashlib.sha256(password.encode()).hexdigest()
    return pwd.hash(password)

def safe_password_verify(password: str, hashed: str) -> bool:
    """
    Verifies password using same pre-hash logic.
    """
    if len(password.encode()) > 72:
        password = hashlib.sha256(password.encode()).hexdigest()
    return pwd.verify(password, hashed)


# --- routes ---

@router.post("/register", response_model=UserOut)
async def register(payload: UserCreate, request: Request):
    print(await request.json())

    # Check if email already exists
    if await users.find_one({"email": payload.email}):
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
    return {
        "id": str(u["_id"]),
        "email": u["email"],
        "role": u.get("role", "user"),
        "profile": u.get("profile", {})
    }


@router.post("/login")
async def login(payload: LoginIn):
    u = await users.find_one({"email": payload.email})
    if not u or not safe_password_verify(payload.password, u["passwordHash"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({
        "user_id": str(u["_id"]),
        "role": u.get("role", "user"),
        "email": u["email"]
    })

    return {"access_token": token, "token_type": "bearer"}


# --- token verification dependency ---
async def get_current_user(authorization: str = Header(...)):
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid auth scheme")
        data = decode_token(token)
        return data
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user
