import random

import pika

animals = ["cat", "dog", "lion", "*"]
actions = ["say", "jump", "eat", "*"]


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

for i in range(1_000):
    animal = random.choice(animals)
    action = random.choice(actions)
    key = f"{animal}.{action}"

    print(f"Producing: {key}")
    channel.basic_publish(
        exchange="animal_action",
        routing_key=key,
        body=f"Producer : {key} : {i}",
    )

connection.close()
