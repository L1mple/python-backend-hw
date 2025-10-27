from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from faker import Faker

faker = Faker()

BASE_URL = "http://localhost:8080"


def create_items():
    """Create random items in the shop"""
    for _ in range(100):
        item = {
            "name": faker.catch_phrase(),
            "price": round(faker.random.uniform(10.0, 500.0), 2),
        }
        response = requests.post(f"{BASE_URL}/item", json=item)
        print(f"Created item: {response.status_code}")


def get_items():
    """Get items with random filters"""
    for _ in range(100):
        params = {}
        if faker.boolean():
            params["min_price"] = faker.random.uniform(0, 100)
        if faker.boolean():
            params["max_price"] = faker.random.uniform(100, 500)
        if faker.boolean():
            params["offset"] = faker.random_int(0, 10)
        if faker.boolean():
            params["limit"] = faker.random_int(1, 20)

        response = requests.get(f"{BASE_URL}/item", params=params)
        print(f"Get items: {response.status_code}")


def create_carts():
    """Create random carts"""
    for _ in range(50):
        response = requests.post(f"{BASE_URL}/cart")
        print(f"Created cart: {response.status_code}")


def add_items_to_carts():
    """Add random items to random carts"""
    for _ in range(200):
        cart_id = faker.random_int(1, 50)
        item_id = faker.random_int(1, 100)
        response = requests.post(f"{BASE_URL}/cart/{cart_id}/add/{item_id}")
        print(f"Add item to cart: {response.status_code}")


def get_carts():
    """Get carts with random filters"""
    for _ in range(100):
        params = {}
        if faker.boolean():
            params["min_price"] = faker.random.uniform(0, 500)
        if faker.boolean():
            params["max_price"] = faker.random.uniform(500, 2000)
        if faker.boolean():
            params["min_quantity"] = faker.random_int(0, 5)
        if faker.boolean():
            params["max_quantity"] = faker.random_int(5, 20)

        response = requests.get(f"{BASE_URL}/cart", params=params)
        print(f"Get carts: {response.status_code}")


def patch_items():
    """Partially update random items"""
    for _ in range(50):
        item_id = faker.random_int(1, 100)
        update = {}
        if faker.boolean():
            update["name"] = faker.catch_phrase()
        if faker.boolean():
            update["price"] = round(faker.random.uniform(10.0, 500.0), 2)

        if update:  # Only send if we have something to update
            response = requests.patch(f"{BASE_URL}/item/{item_id}", json=update)
            print(f"Patch item: {response.status_code}")


def delete_items():
    """Delete random items"""
    for _ in range(20):
        item_id = faker.random_int(1, 100)
        response = requests.delete(f"{BASE_URL}/item/{item_id}")
        print(f"Delete item: {response.status_code}")


print("Starting load test...")

with ThreadPoolExecutor(max_workers=100) as executor:
    futures = {}

    # Submit various tasks
    for i in range(5):
        futures[executor.submit(create_items)] = f"create-items-{i}"

    for i in range(10):
        futures[executor.submit(get_items)] = f"get-items-{i}"

    for i in range(3):
        futures[executor.submit(create_carts)] = f"create-carts-{i}"

    for i in range(10):
        futures[executor.submit(add_items_to_carts)] = f"add-items-{i}"

    for i in range(8):
        futures[executor.submit(get_carts)] = f"get-carts-{i}"

    for i in range(4):
        futures[executor.submit(patch_items)] = f"patch-items-{i}"

    for i in range(2):
        futures[executor.submit(delete_items)] = f"delete-items-{i}"

    # Wait for completion
    for future in as_completed(futures):
        print(f"✓ Completed {futures[future]}")

print("\nLoad test completed!")
