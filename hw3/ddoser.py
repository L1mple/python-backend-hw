from concurrent.futures import ThreadPoolExecutor
import requests
from faker import Faker

faker = Faker()

def create_items():
    for _ in range(500):
        response = requests.post(
            "http://localhost:8080/item",
            json={"name": faker.word(), "price": faker.pyfloat(min_value=1, max_value=100, positive=True)}
        )
        print(f"Create item: {response.status_code}")

def create_carts_and_add():
    for _ in range(500):
        cart_response = requests.post("http://localhost:8080/cart")
        if cart_response.status_code == 201:
            cart_id = cart_response.json()["id"]
            item_id = faker.random_int(min=1, max=50)
            response = requests.post(f"http://localhost:8080/cart/{cart_id}/add/{item_id}")
            print(f"Add to cart: {response.status_code}")

with ThreadPoolExecutor() as executor:
    for _ in range(5):
        executor.submit(create_items)
        executor.submit(create_carts_and_add)