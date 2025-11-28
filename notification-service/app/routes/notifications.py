from fastapi import APIRouter, HTTPException, Query, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from bson import ObjectId
from ..db import notifications
from ..schemas import NotificationOut, NotificationSend
from ..auth import verify_token
from ..cache import cache, invalidate_cache
import datetime

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
limiter = Limiter(key_func=get_remote_address)

@router.get("", response_model=list[NotificationOut])
@limiter.limit("60/minute")
async def list_notifications(
    request: Request,
    user=Depends(verify_token),
    limit: int = Query(50, le=200),
    delivered: bool | None = None,
    type: str | None = None,
    priority: str | None = None
):
    """Get user's notifications with optional filters"""
    # Build cache key
    cache_key = f"notifications:user:{user.get('user_id')}:delivered:{delivered}:type:{type}:priority:{priority}:limit:{limit}"
    
    # Try cache first
    cached_notifications = cache.get(cache_key)
    if cached_notifications:
        return cached_notifications
    
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
    
    # Cache the result (shorter TTL for notifications)
    cache.set(cache_key, result, ttl=300)
    
    return result


@router.get("/unread-count")
@limiter.limit("120/minute")
async def get_unread_count(request: Request, user=Depends(verify_token)):
    """Get count of undelivered notifications"""
    # Try cache first
    cache_key = f"notifications:unread:user:{user.get('user_id')}"
    cached_count = cache.get(cache_key)
    if cached_count is not None:
        return {"count": cached_count}
    
    count = await notifications.count_documents({
        "userId": user.get("user_id"),
        "delivered": False
    })
    
    # Cache for 1 minute
    cache.set(cache_key, count, ttl=60)
    
    return {"count": count}


@router.get("/{notification_id}", response_model=NotificationOut)
@limiter.limit("60/minute")
async def get_notification(request: Request, notification_id: str, user=Depends(verify_token)):
    """Get a specific notification"""
    # Try cache first
    cache_key = f"notification:id:{notification_id}"
    cached_notif = cache.get(cache_key)
    
    if cached_notif:
        # Check ownership
        if user.get("user_id") != cached_notif.get("userId"):
            raise HTTPException(403, "Forbidden")
        return cached_notif
    
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
    
    notif_data = {"id": str(notif["_id"]), **{k:v for k,v in notif.items() if k!="_id"}}
    
    # Cache it
    cache.set(cache_key, notif_data, ttl=300)
    
    return notif_data


@router.patch("/{notification_id}/mark-delivered")
@limiter.limit("60/minute")
async def mark_delivered(request: Request, notification_id: str, user=Depends(verify_token)):
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
    
    # Invalidate caches
    invalidate_cache(f"notification:id:{notification_id}")
    invalidate_cache(f"notifications:user:{user.get('user_id')}:*")
    invalidate_cache(f"notifications:unread:user:{user.get('user_id')}")
    
    return {"status": "success", "message": "Notification marked as delivered"}


@router.patch("/{notification_id}/mark-read")
@limiter.limit("60/minute")
async def mark_read(request: Request, notification_id: str, user=Depends(verify_token)):
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
    
    # Invalidate caches
    invalidate_cache(f"notification:id:{notification_id}")
    invalidate_cache(f"notifications:user:{user.get('user_id')}:*")
    invalidate_cache(f"notifications:unread:user:{user.get('user_id')}")
    
    return {"status": "success", "message": "Notification marked as read"}


@router.post("/mark-all-read")
@limiter.limit("30/minute")
async def mark_all_read(request: Request, user=Depends(verify_token)):
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
    
    # Invalidate all notification caches for this user
    invalidate_cache(f"notifications:user:{user.get('user_id')}:*")
    invalidate_cache(f"notifications:unread:user:{user.get('user_id')}")
    
    return {
        "status": "success", 
        "message": f"Marked {result.modified_count} notifications as read"
    }


@router.delete("/{notification_id}")
@limiter.limit("30/minute")
async def delete_notification(request: Request, notification_id: str, user=Depends(verify_token)):
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
    
    # Invalidate caches
    invalidate_cache(f"notification:id:{notification_id}")
    invalidate_cache(f"notifications:user:{user.get('user_id')}:*")
    invalidate_cache(f"notifications:unread:user:{user.get('user_id')}")
    
    return {"status": "success", "message": "Notification deleted"}


@router.post("/send")
@limiter.limit("20/minute")
async def send_notification(request: Request, payload: NotificationSend, user=Depends(verify_token)):
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
    
    # Invalidate user's notification caches
    invalidate_cache(f"notifications:user:{payload.userId}:*")
    invalidate_cache(f"notifications:unread:user:{payload.userId}")
    
    return {"status": "success", "notification": notif}