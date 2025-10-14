from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "user"
    profile: Optional[dict] = None

class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: str
    profile: Optional[dict] = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str
