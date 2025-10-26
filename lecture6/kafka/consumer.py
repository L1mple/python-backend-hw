import signal
import sys
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from os import name

from confluent_kafka import Consumer

consumer_num = int(sys.argv[1])


@dataclass(slots=True)
class KafkaConsumer:
    name: str
    topic: str
    group: str
    server: str

    consumer: Consumer = field(init=False)

    def __post_init__(self) -> None:
        self.consumer = Consumer(
            {
                "bootstrap.servers": "localhost:29092",
                "group.id": self.group,
                "auto.offset.reset": "earliest",
            }
        )
        self.consumer.subscribe([self.topic])

    def run(self) -> None:
        print(f"Starting consumer {self.name}")

        while True:
            print("waiting")
            message = self.consumer.poll(1.0)

            if message is None:
                continue
            if message.error():
                print(f"Err {message.error()}")
                continue

            print(f"CONSUMER-{self.name}: {message.value().decode()}")

    def stop(self) -> None:
        self.consumer.close()


if __name__ == "__main__":
    with ThreadPoolExecutor() as e:
        consumers = [
            KafkaConsumer(
                name=str(i),
                topic="demo-topic",
                group="demo.group",
                server="localhost:29092",
            )
            for i in range(consumer_num)
        ]
        signal.signal(
            signal.SIGTSTP,
            lambda _, __: [consumer.stop() for consumer in consumers],
        )

        futures = [e.submit(lambda: consumer.run()) for consumer in consumers]

        wait(futures)
