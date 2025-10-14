import os, pika, json, asyncio, time
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongos:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.get_database("banking")
notifications = db.notifications

RABBIT_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBIT_USER = os.getenv("RABBITMQ_USER", "guest")
RABBIT_PASS = os.getenv("RABBITMQ_PASS", "guest")

def callback(ch, method, properties, body):
    data = json.loads(body)
    print(f"Received notification: {data}")
    
    # Insert into Mongo (use asyncio event loop)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(notifications.insert_one({
            "userId": data.get("userId"),
            "type": data.get("type"),
            "payload": data.get("payload"),
            "delivered": False,
            "createdAt": data.get("createdAt")
        }))
        print(f"Notification stored for user: {data.get('userId')}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error storing notification: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    finally:
        loop.close()

def run():
    print("Starting Notification Consumer...")
    
    # Wait for RabbitMQ to be ready
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
            ch.queue_declare(queue="notifications", durable=True)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(queue="notifications", on_message_callback=callback)
            print("Notification consumer connected and listening...")
            ch.start_consuming()
            break
        except Exception as e:
            retry_count += 1
            print(f"Connection attempt {retry_count}/{max_retries} failed: {e}")
            if retry_count < max_retries:
                time.sleep(5)
            else:
                print("Failed to connect to RabbitMQ after maximum retries")
                raise

if __name__ == "__main__":
    run()