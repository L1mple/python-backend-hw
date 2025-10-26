from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from faker import Faker

faker = Faker()


def create_items():
    for _ in range(500):
        response = requests.post(
            "http://localhost:8080/item",
            json={
                "name": faker.word().capitalize(),
                "price": round(faker.random.uniform(10.0, 1000.0), 2),
            },
        )
        print(response)


def get_items():
    for _ in range(500):
        response = requests.get(
            "http://localhost:8080/item",
            params={
                "offset": faker.random_number(digits=1),
                "limit": faker.random_number(digits=1, fix_len=True),
            },
        )
        print(response)


def create_carts():
    for _ in range(200):
        response = requests.post("http://localhost:8080/cart")
        print(response)


def add_items_to_carts():
    for _ in range(300):
        cart_id = faker.random_number(digits=2)
        item_id = faker.random_number(digits=2)
        response = requests.post(f"http://localhost:8080/cart/{cart_id}/add/{item_id}")
        print(response)


with ThreadPoolExecutor() as executor:
    futures = {}

    for i in range(10):
        futures[executor.submit(create_items)] = f"create-items-{i}"

    for i in range(10):
        futures[executor.submit(get_items)] = f"get-items-{i}"

    for i in range(5):
        futures[executor.submit(create_carts)] = f"create-carts-{i}"

    for i in range(5):
        futures[executor.submit(add_items_to_carts)] = f"add-to-carts-{i}"

    for future in as_completed(futures):
        print(f"completed {futures[future]}")
