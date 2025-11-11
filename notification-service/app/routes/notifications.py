# from fastapi import APIRouter, HTTPException, Query, Depends
# from bson import ObjectId
# from ..db import notifications
# from ..schemas import NotificationOut, NotificationSend
# from ..auth import verify_token
# import datetime

# router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# @router.get("", response_model=list[NotificationOut])
# async def list_notifications(
#     user=Depends(verify_token),
#     limit: int = Query(50, le=200),
#     delivered: bool | None = None
# ):
#     # Users can only see their own notifications
#     q = {"userId": user.get("user_id")}
    
#     if delivered is not None:
#         q["delivered"] = delivered
    
#     cur = notifications.find(q).sort("createdAt", -1).limit(limit)
#     result = []
#     async for notif in cur:
#         notif["id"] = str(notif["_id"])
#         notif.pop("_id", None)
#         result.append(notif)
    
#     return result

# @router.patch("/{notification_id}/mark-delivered")
# async def mark_delivered(notification_id: str, user=Depends(verify_token)):
#     try:
#         notif_obj_id = ObjectId(notification_id)
#     except:
#         raise HTTPException(400, "Invalid notification ID")
    
#     notif = await notifications.find_one({"_id": notif_obj_id})
#     if not notif:
#         raise HTTPException(404, "Notification not found")
    
#     # Users can only update their own notifications
#     if user.get("user_id") != notif.get("userId"):
#         raise HTTPException(403, "Forbidden")
    
#     await notifications.update_one(
#         {"_id": notif_obj_id},
#         {"$set": {"delivered": True, "deliveredAt": datetime.datetime.utcnow()}}
#     )
    
#     return {"status": "success", "message": "Notification marked as delivered"}

# @router.post("/send")
# async def send_notification(payload: NotificationSend, user=Depends(verify_token)):
#     # Only admin can manually send notifications
#     if user.get("role") != "admin":
#         raise HTTPException(403, "Forbidden: admin only")
    
#     notif = {
#         "userId": payload.userId,
#         "type": payload.type,
#         "payload": payload.payload,
#         "delivered": False,
#         "createdAt": datetime.datetime.utcnow()
#     }
    
#     res = await notifications.insert_one(notif)
#     notif["id"] = str(res.inserted_id)
#     notif.pop("_id", None)
    
#     return {"status": "success", "notification": notif}

from fastapi import APIRouter, HTTPException, Query, Depends
from bson import ObjectId
from ..db import notifications
from ..schemas import NotificationOut, NotificationSend
from ..auth import verify_token
import datetime

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    user=Depends(verify_token),
    limit: int = Query(50, le=200),
    delivered: bool | None = None,
    type: str | None = None,
    priority: str | None = None
):
    """Get user's notifications with optional filters"""
    q = {"userId": user.get("user_id")}
    
    if delivered is not None:
        q["delivered"] = delivered
    
    if type:
        q["type"] = type
    
    if priority:
        q["priority"] = priority
    
    cur = notifications.find(q).sort("createdAt", -1).limit(limit)
    result = []
    async for notif in cur:
        notif["id"] = str(notif["_id"])
        notif.pop("_id", None)
        result.append(notif)
    
    return result

@router.get("/unread-count")
async def get_unread_count(user=Depends(verify_token)):
    """Get count of undelivered notifications"""
    count = await notifications.count_documents({
        "userId": user.get("user_id"),
        "delivered": False
    })
    return {"count": count}

@router.get("/{notification_id}", response_model=NotificationOut)
async def get_notification(notification_id: str, user=Depends(verify_token)):
    """Get a specific notification"""
    try:
        notif_obj_id = ObjectId(notification_id)
    except:
        raise HTTPException(400, "Invalid notification ID")
    
    notif = await notifications.find_one({"_id": notif_obj_id})
    if not notif:
        raise HTTPException(404, "Notification not found")
    
    # Check ownership
    if user.get("user_id") != notif.get("userId"):
        raise HTTPException(403, "Forbidden")
    
    notif["id"] = str(notif["_id"])
    notif.pop("_id", None)
    return notif

@router.patch("/{notification_id}/mark-delivered")
async def mark_delivered(notification_id: str, user=Depends(verify_token)):
    """Mark notification as delivered"""
    try:
        notif_obj_id = ObjectId(notification_id)
    except:
        raise HTTPException(400, "Invalid notification ID")
    
    notif = await notifications.find_one({"_id": notif_obj_id})
    if not notif:
        raise HTTPException(404, "Notification not found")
    
    if user.get("user_id") != notif.get("userId"):
        raise HTTPException(403, "Forbidden")
    
    await notifications.update_one(
        {"_id": notif_obj_id},
        {"$set": {
            "delivered": True, 
            "deliveredAt": datetime.datetime.utcnow()
        }}
    )
    
    return {"status": "success", "message": "Notification marked as delivered"}

@router.patch("/{notification_id}/mark-read")
async def mark_read(notification_id: str, user=Depends(verify_token)):
    """Mark notification as read"""
    try:
        notif_obj_id = ObjectId(notification_id)
    except:
        raise HTTPException(400, "Invalid notification ID")
    
    notif = await notifications.find_one({"_id": notif_obj_id})
    if not notif:
        raise HTTPException(404, "Notification not found")
    
    if user.get("user_id") != notif.get("userId"):
        raise HTTPException(403, "Forbidden")
    
    update_data = {"readAt": datetime.datetime.utcnow()}
    
    # Also mark as delivered if not already
    if not notif.get("delivered"):
        update_data["delivered"] = True
        update_data["deliveredAt"] = datetime.datetime.utcnow()
    
    await notifications.update_one(
        {"_id": notif_obj_id},
        {"$set": update_data}
    )
    
    return {"status": "success", "message": "Notification marked as read"}

@router.post("/mark-all-read")
async def mark_all_read(user=Depends(verify_token)):
    """Mark all user's notifications as read"""
    result = await notifications.update_many(
        {
            "userId": user.get("user_id"),
            "delivered": False
        },
        {"$set": {
            "delivered": True,
            "deliveredAt": datetime.datetime.utcnow(),
            "readAt": datetime.datetime.utcnow()
        }}
    )
    
    return {
        "status": "success", 
        "message": f"Marked {result.modified_count} notifications as read"
    }

@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, user=Depends(verify_token)):
    """Delete a notification"""
    try:
        notif_obj_id = ObjectId(notification_id)
    except:
        raise HTTPException(400, "Invalid notification ID")
    
    notif = await notifications.find_one({"_id": notif_obj_id})
    if not notif:
        raise HTTPException(404, "Notification not found")
    
    if user.get("user_id") != notif.get("userId"):
        raise HTTPException(403, "Forbidden")
    
    await notifications.delete_one({"_id": notif_obj_id})
    
    return {"status": "success", "message": "Notification deleted"}

@router.post("/send")
async def send_notification(payload: NotificationSend, user=Depends(verify_token)):
    """Manually send a notification (admin only)"""
    if user.get("role") != "admin":
        raise HTTPException(403, "Forbidden: admin only")
    
    notif = {
        "userId": payload.userId,
        "type": payload.type,
        "payload": payload.payload,
        "delivered": False,
        "createdAt": datetime.datetime.utcnow(),
        "deliveredAt": None,
        "readAt": None,
        "priority": getattr(payload, 'priority', 'normal'),
        "channel": getattr(payload, 'channel', 'in-app'),
        "metadata": getattr(payload, 'metadata', {})
    }
    
    res = await notifications.insert_one(notif)
    notif["id"] = str(res.inserted_id)
    notif.pop("_id", None)
    
    return {"status": "success", "notification": notif}