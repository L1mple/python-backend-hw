import sys

import pika

queue = sys.argv[1]
queue_name = f"queue_{queue}"
parameters = pika.ConnectionParameters(
    host="localhost",
    credentials=pika.PlainCredentials(
        username="admin",
        password="adminpass",
    ),
)
connection = pika.BlockingConnection(parameters=parameters)
channel = connection.channel()

channel.queue_declare(queue=queue_name)


def callback(ch, method, properties, body):
    print(f"CONSUMER: Received {body}")


channel.basic_consume(
    queue=queue_name,
    on_message_callback=callback,
    auto_ack=True,
)

print(f"CONSUMER: {queue_name} Waiting for messages")
channel.start_consuming()
