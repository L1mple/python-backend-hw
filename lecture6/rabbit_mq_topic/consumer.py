import sys

import pika
import pika.exchange_type

animal = sys.argv[1]
action = sys.argv[2]
key = f"{animal}.{action}"

parameters = pika.ConnectionParameters(
    host="localhost",
    credentials=pika.PlainCredentials(
        username="admin",
        password="adminpass",
    ),
)
connection = pika.BlockingConnection(parameters=parameters)
channel = connection.channel()

channel.exchange_declare(
    exchange="animal_action",
    exchange_type="topic",
)

result = channel.queue_declare("", exclusive=True)
queue_name = result.method.queue

channel.queue_bind(
    exchange="animal_action",
    queue=queue_name,
    routing_key=key,
)


def callback(ch, method, properties, body):
    print(f"CONSUMER[{key}]: Received {body}")


channel.basic_consume(
    queue=queue_name,
    on_message_callback=callback,
    auto_ack=True,
)

print(f"CONSUMER: [key: {key}] Waiting for messages")
channel.start_consuming()
