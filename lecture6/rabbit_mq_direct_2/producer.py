from concurrent.futures import ThreadPoolExecutor, wait

import pika
import pika.exchange_type


def produce_many(key: str, i: int):
    producer_name = f"Producer {key}-{i}"
    print(producer_name)
    queue_name = f"queue_{key}"

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
        "direct_wb",
        exchange_type=pika.exchange_type.ExchangeType.direct,
    )
    channel.queue_declare(queue=queue_name)
    channel.queue_bind(
        exchange='direct_wb',
        queue=queue_name,
        routing_key=key,
    )

    for i in range(1_000):
        channel.basic_publish(
            exchange="direct_wb",
            routing_key=key,
            body=f"{producer_name} : {i}",
        )

    connection.close()


with ThreadPoolExecutor() as e:
    futures = [e.submit(produce_many, "black", i) for i in range(5)]
    futures = [e.submit(produce_many, "white", i) for i in range(5)]

    wait(futures)

    print("completed")
