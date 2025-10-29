from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time

import requests
from faker import Faker


TARGET_HOST = os.getenv("TARGET_HOST", "http://localhost:8000")

faker = Faker()


def create_items(n: int = 500):
    for _ in range(n):
        name = faker.word()
        price = round(faker.pyfloat(left_digits=2, right_digits=2, positive=True), 2)
        try:
            r = requests.post(
                f"{TARGET_HOST}/item",
                json={"name": name, "price": price},
                timeout=5,
            )
            print("create_item", r.status_code)
        except Exception as e:
            print("create_item error", e)


def mutate_carts(n: int = 500):
    # ensure at least one cart exists
    try:
        rc = requests.post(f"{TARGET_HOST}/cart", timeout=5)
        base_cart_id = rc.json().get("id", 1) if rc.ok else 1
    except Exception:
        base_cart_id = 1
    for _ in range(n):
        try:
            cart_id = faker.random_int(min=base_cart_id, max=base_cart_id + 10)
            item_id = faker.random_int(min=1, max=200)
            r = requests.post(f"{TARGET_HOST}/cart/{cart_id}/add/{item_id}", timeout=5)
            print("add_to_cart", r.status_code)
        except Exception as e:
            print("add_to_cart error", e)


def get_lists(n: int = 500):
    for _ in range(n):
        try:
            r1 = requests.get(f"{TARGET_HOST}/item", timeout=5)
            r2 = requests.get(f"{TARGET_HOST}/cart", timeout=5)
            print("list", r1.status_code, r2.status_code)
        except Exception as e:
            print("list error", e)


def main():
    workers = int(os.getenv("WORKERS", "20"))
    batch = int(os.getenv("BATCH", "500"))
    print(f"Target: {TARGET_HOST}, workers={workers}, batch={batch}")
    start = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for i in range(workers // 2):
            futures[executor.submit(create_items, batch)] = f"create-items-{i}"
        for i in range(workers // 2):
            futures[executor.submit(mutate_carts, batch)] = f"mutate-carts-{i}"
        futures[executor.submit(get_lists, batch)] = "get-lists"
        for fut in as_completed(futures):
            print("completed", futures[fut])
    print(f"done in {time.time()-start:.2f}s")


if __name__ == "__main__":
    main()

