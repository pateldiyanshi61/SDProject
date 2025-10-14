import os, json, pika

RABBIT_HOST = os.getenv("RABBITMQ_HOST","rabbitmq")
RABBIT_USER = os.getenv("RABBITMQ_USER","guest")
RABBIT_PASS = os.getenv("RABBITMQ_PASS","guest")

def publish_notification(message: dict, queue="notifications"):
    creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    params = pika.ConnectionParameters(host=RABBIT_HOST, credentials=creds)
    conn = pika.BlockingConnection(params)
    ch = conn.channel()
    ch.queue_declare(queue=queue, durable=True)
    ch.basic_publish(exchange="", routing_key=queue, body=json.dumps(message),
                     properties=pika.BasicProperties(delivery_mode=2))
    conn.close()
