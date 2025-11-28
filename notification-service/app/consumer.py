import os, pika, json, asyncio, time
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import threading

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongos:27017")

RABBIT_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBIT_USER = os.getenv("RABBITMQ_USER", "guest")
RABBIT_PASS = os.getenv("RABBITMQ_PASS", "guest")

# Global MongoDB client and event loop
mongo_client = None
notifications_collection = None
event_loop = None
loop_thread = None

def init_mongo():
    """Initialize MongoDB client"""
    global mongo_client, notifications_collection
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    db = mongo_client.get_database("banking")
    notifications_collection = db.notifications
    print("✅ MongoDB client initialized")

def start_event_loop():
    """Start event loop in a separate thread"""
    global event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()

def init_event_loop():
    """Initialize event loop in a background thread"""
    global loop_thread
    loop_thread = threading.Thread(target=start_event_loop, daemon=True)
    loop_thread.start()
    time.sleep(0.1)  # Give the loop time to start
    print("✅ Event loop initialized in background thread")

async def store_notification(data):
    """Async function to store notification in MongoDB"""
    # Parse createdAt if it's a string
    created_at = data.get("createdAt")
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            created_at = datetime.utcnow()
    elif not created_at:
        created_at = datetime.utcnow()
    
    notification_doc = {
        "userId": data.get("userId"),
        "type": data.get("type"),
        "payload": data.get("payload", {}),
        "delivered": False,
        "createdAt": created_at,
        "deliveredAt": None,
        "readAt": None,
        "priority": data.get("priority", "normal"),
        "channel": data.get("channel", "in-app"),
        "metadata": data.get("metadata", {})
    }
    
    result = await notifications_collection.insert_one(notification_doc)
    return result

def callback(ch, method, properties, body):
    """Process incoming notification messages"""
    try:
        data = json.loads(body)
        print(f"📨 Received notification: {data.get('type')} for user {data.get('userId')}")
        
        try:
            # Schedule the coroutine in the event loop running in the background thread
            future = asyncio.run_coroutine_threadsafe(
                store_notification(data),
                event_loop
            )
            # Wait for the result (with timeout)
            future.result(timeout=10)
            
            print(f"✅ Notification stored for user: {data.get('userId')}")
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            print(f"❌ Error storing notification: {e}")
            import traceback
            traceback.print_exc()
            # Reject and requeue the message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in message: {e}")
        # Don't requeue invalid messages
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"❌ Unexpected error in callback: {e}")
        import traceback
        traceback.print_exc()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def run():
    """Start the notification consumer"""
    print("🚀 Starting Notification Consumer...")
    
    # Initialize MongoDB and event loop
    init_mongo()
    init_event_loop()
    
    max_retries = 10
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
            params = pika.ConnectionParameters(
                host=RABBIT_HOST, 
                credentials=creds,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            conn = pika.BlockingConnection(params)
            ch = conn.channel()
            
            # Declare notifications queue
            ch.queue_declare(queue="notifications", durable=True)
            
            # Set prefetch count for better load distribution
            ch.basic_qos(prefetch_count=1)
            
            # Start consuming
            ch.basic_consume(queue="notifications", on_message_callback=callback)
            
            print("✅ Notification consumer connected and listening on 'notifications' queue...")
            ch.start_consuming()
            break
            
        except KeyboardInterrupt:
            print("⛔ Consumer stopped by user")
            # Clean up
            if event_loop and not event_loop.is_closed():
                event_loop.call_soon_threadsafe(event_loop.stop)
            if mongo_client:
                mongo_client.close()
            break
        except Exception as e:
            retry_count += 1
            print(f"⚠️ Connection attempt {retry_count}/{max_retries} failed: {e}")
            if retry_count < max_retries:
                print(f"⏳ Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("❌ Failed to connect to RabbitMQ after maximum retries")
                # Clean up
                if event_loop and not event_loop.is_closed():
                    event_loop.call_soon_threadsafe(event_loop.stop)
                if mongo_client:
                    mongo_client.close()
                raise

if __name__ == "__main__":
    run()