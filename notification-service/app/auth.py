import os
import jwt
from fastapi import Header, HTTPException

JWT_SECRET = os.getenv("JWT_SECRET", "your_super_secret_jwt_key_change_in_production")
ALGO = "HS256"

async def verify_token(authorization: str = Header(...)):
    """Verify JWT token and return decoded payload"""
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "Invalid authorization header")
        
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    except Exception as e:
        raise HTTPException(401, f"Authentication failed: {str(e)}")