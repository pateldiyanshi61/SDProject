from fastapi import APIRouter, HTTPException, Header, Depends, Request
from passlib.context import CryptContext
from ..db import users
from ..schemas import UserCreate, UserOut, LoginIn
from ..services.jwt_utils import create_access_token, decode_token
from bson import ObjectId

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserOut)
async def register(payload: UserCreate, request: Request):
    print(await request.json())
    if await users.find_one({"email": payload.email}):
        raise HTTPException(400, "Email exists")
    pw_hash = pwd.hash(payload.password)
    res = await users.insert_one({
        "email": payload.email,
        "passwordHash": pw_hash,
        "role": payload.role,
        "profile": payload.profile or {},
        "createdAt": None
    })
    u = await users.find_one({"_id": res.inserted_id})
    return {"id": str(u["_id"]), "email": u["email"], "role": u.get("role","user"), "profile": u.get("profile", {})}

@router.post("/login")
async def login(payload: LoginIn):
    u = await users.find_one({"email": payload.email})
    if not u or not pwd.verify(payload.password, u["passwordHash"]):
        raise HTTPException(400, "Invalid credentials")
    token = create_access_token({"user_id": str(u["_id"]), "role": u.get("role","user"), "email": u["email"]})
    return {"access_token": token, "token_type": "bearer"}

# simple dependency to get current user
async def get_current_user(authorization: str = Header(...)):
    try:
        scheme, token = authorization.split()
        data = decode_token(token)
        return data
    except Exception:
        raise HTTPException(401, "Invalid token")

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user
