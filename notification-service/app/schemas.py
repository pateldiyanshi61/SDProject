from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NotificationOut(BaseModel):
    id: str
    userId: str
    type: str
    payload: dict
    delivered: bool
    createdAt: Optional[datetime] = None

class NotificationSend(BaseModel):
    userId: str
    type: str
    payload: dict