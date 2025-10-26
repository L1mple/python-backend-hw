import pika

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
    exchange="test.fanout",
    exchange_type="fanout",
)

channel.queue_declare(queue="queue_name")

channel.queue_bind(
    queue="queue_name",
    exchange="test.fanout",
)

for i in range(1):
    channel.basic_publish(
        exchange="test.fanout",
        routing_key='lol',
        body=f"Producer : {i}",
    )

connection.close()
