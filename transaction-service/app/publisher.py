import os, json, pika, time
from typing import Optional

RABBIT_HOST = os.getenv("RABBITMQ_HOST","rabbitmq")
RABBIT_USER = os.getenv("RABBITMQ_USER","guest")
RABBIT_PASS = os.getenv("RABBITMQ_PASS","guest")

def get_channel():
    """Get RabbitMQ channel with retry logic"""
    max_retries = 5
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
            return conn, conn.channel()
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(2)
            else:
                raise

def publish_notification(message: dict, queue="notifications"):
    """Publish notification to queue"""
    try:
        conn, ch = get_channel()
        ch.queue_declare(queue=queue, durable=True)
        ch.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        conn.close()
    except Exception as e:
        print(f"Failed to publish notification: {e}")
        raise

def publish_error(message: dict, queue="transaction_errors"):
    """Publish transaction error to error queue"""
    try:
        conn, ch = get_channel()
        ch.queue_declare(queue=queue, durable=True)
        ch.basic_publish(
            exchange="",
            routing_key=queue,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        conn.close()
    except Exception as e:
        print(f"Failed to publish error: {e}")
        raise