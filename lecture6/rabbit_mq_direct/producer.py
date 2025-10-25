from concurrent.futures import ThreadPoolExecutor, wait

import pika


def produce_many(producer_name: str):
    parameters = pika.ConnectionParameters(
        host="localhost",
        credentials=pika.PlainCredentials(
            username="admin",
            password="adminpass",
        ),
    )
    connection = pika.BlockingConnection(parameters=parameters)
    channel = connection.channel()

    channel.queue_declare(queue="hello")

    for i in range(1_000):
        channel.basic_publish(
            exchange="",
            routing_key="hello",
            body=f"{producer_name} : {i}",
        )

    connection.close()


with ThreadPoolExecutor() as e:
    futures = [e.submit(produce_many, f"Producer {i}") for i in range(2)]
    wait(futures)

    print("completed")
