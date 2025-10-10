from concurrent.futures import ThreadPoolExecutor, as_completed
from random import randint, random
from typing import List

import requests
from faker import Faker


BASE_URL = "http://localhost:8000"

faker = Faker()


def create_items(num_items: int = 300) -> List[int]:
    """Create items via POST /item and return their ids."""
    created_ids: List[int] = []
    for i in range(num_items):
        name = f"{faker.word()}-{i}"
        price = round(10 + random() * 490, 2)
        try:
            resp = requests.post(f"{BASE_URL}/item", json={"name": name, "price": price}, timeout=5)
            if resp.ok:
                created_ids.append(resp.json()["id"])
        except Exception:
            pass
    return created_ids


def create_carts_and_add(items: List[int], num_carts: int = 100, ops_per_cart: int = 10) -> None:
    """Create carts and add random items into them using POST /cart and /cart/{id}/add/{item_id}."""
    for _ in range(num_carts):
        try:
            cart_resp = requests.post(f"{BASE_URL}/cart", timeout=5)
            if not cart_resp.ok:
                continue
            cart_id = cart_resp.json()["id"]
            for _ in range(ops_per_cart):
                if not items:
                    break
                item_id = items[randint(0, len(items) - 1)]
                requests.post(f"{BASE_URL}/cart/{cart_id}/add/{item_id}", timeout=5)
        except Exception:
            pass


def read_lists(iterations: int = 400) -> None:
    """Generate read load for /item and /cart list endpoints."""
    for _ in range(iterations):
        try:
            requests.get(f"{BASE_URL}/item", params={"offset": 0, "limit": 10}, timeout=5)
            requests.get(f"{BASE_URL}/cart", params={"offset": 0, "limit": 10}, timeout=5)
        except Exception:
            pass


def main() -> None:
    items = create_items(num_items=300)

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {}
        for i in range(10):
            futures[executor.submit(create_carts_and_add, items, 30, 15)] = f"carts+adds-{i}"
        for i in range(10):
            futures[executor.submit(read_lists, 500)] = f"reads-{i}"
        for future in as_completed(futures):
            print(f"completed {futures[future]}")


if __name__ == "__main__":
    main()
