import os, pika, json, asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI","mongodb://mongo-db:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client.get_database("banking")
notifications = db.notifications

RABBIT_HOST = os.getenv("RABBITMQ_HOST","rabbitmq")
RABBIT_USER = os.getenv("RABBITMQ_USER","guest")
RABBIT_PASS = os.getenv("RABBITMQ_PASS","guest")

def callback(ch, method, properties, body):
    data = json.loads(body)
    print("Received notification:", data)
    # Insert into Mongo (use asyncio event loop)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(notifications.insert_one({
        "userId": data.get("userId"),
        "type": data.get("type"),
        "payload": data.get("payload"),
        "delivered": False,
        "createdAt": data.get("createdAt")
    }))
    ch.basic_ack(delivery_tag=method.delivery_tag)

def run():
    creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    params = pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.queue_declare(queue="notifications", durable=True)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue="notifications", on_message_callback=callback)
    print("Notification consumer started")
    ch.start_consuming()

if __name__ == "__main__":
    run()
