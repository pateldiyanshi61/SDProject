import os, jwt, datetime

SECRET = os.getenv("JWT_SECRET", "CHANGE_THIS_SECRET")
ALGO = "HS256"

def create_access_token(data: dict, expires_minutes: int = 60):
    payload = data.copy()
    payload.update({"exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_minutes)})
    return jwt.encode(payload, SECRET, algorithm=ALGO)

def decode_token(token: str):
    return jwt.decode(token, SECRET, algorithms=[ALGO])
