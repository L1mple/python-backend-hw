import sys

from confluent_kafka import Producer

topic = sys.argv[1]
producer = Producer({"bootstrap.servers": "localhost:29092"})


# def delivery_report(err, msg):
#     if err is not None:
#         print(f"Err: {err}")
#     else:
#         print(f"Delivered {msg.topic()} [{msg.partition()}]")


for i in range(10_000):
    producer.poll(0)
    producer.produce(
        topic,
        key=str(i),
        value=f"Message {i}".encode(),
    )


producer.flush()
