from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from faker import Faker

faker = Faker()

import random

def random_name():
    names = ["Хлеб", "Молоко", "Масло", "Мыло"]
    return f"{random.choice(names)}"


def create_users():
    for _ in range(100):
        response = requests.post(
            "http://localhost:8080/item",
            json={
                "name": random_name(),
                "price": random.randint(10, 1000)

            },
        )

        print(response)


def get_items():
    for _ in range(100):
        response = requests.post(
            "http://localhost:8080/nonexistent-endpoint",
            params={"id": random.randint(1, 100)},
        )
        print(f"Status: {response.status_code}")


with ThreadPoolExecutor() as executor:
    futures = {}

    for i in range(15):
        futures[executor.submit(create_users)] = f"create-user-{i}"

    for _ in range(15):
        futures[executor.submit(get_items)] = f"get-users-{i}"

    for future in as_completed(futures):
        print(f"completed {futures[future]}")
