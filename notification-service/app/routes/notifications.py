from fastapi import APIRouter, HTTPException, Query, Depends
from ..db import notifications
from ..schemas import NotificationOut, NotificationSend
from ..auth import verify_token
import datetime

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    user=Depends(verify_token),
    limit: int = Query(50, le=200),
    delivered: bool | None = None
):
    # Users can only see their own notifications
    q = {"userId": user.get("user_id")}
    
    if delivered is not None:
        q["delivered"] = delivered
    
    cur = notifications.find(q).sort("createdAt", -1).limit(limit)
    result = []
    async for notif in cur:
        notif["id"] = str(notif["_id"])
        notif.pop("_id", None)
        result.append(notif)
    
    return result

@router.post("/send")
async def send_notification(payload: NotificationSend, user=Depends(verify_token)):
    # Only admin can manually send notifications
    if user.get("role") != "admin":
        raise HTTPException(403, "Forbidden: admin only")
    
    notif = {
        "userId": payload.userId,
        "type": payload.type,
        "payload": payload.payload,
        "delivered": False,
        "createdAt": datetime.datetime.utcnow()
    }
    
    res = await notifications.insert_one(notif)
    notif["id"] = str(res.inserted_id)
    notif.pop("_id", None)
    
    return {"status": "success", "notification": notif}