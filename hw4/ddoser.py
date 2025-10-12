from concurrent.futures import ThreadPoolExecutor

import requests
from faker import Faker

faker = Faker()  # для генерации фейковых данных


def create_carts_and_items():
    for _ in range(100):  # создаём 100 корзин и товаров
        # создать товар
        item = {"name": faker.word(), "price": faker.random_number(digits=2)}
        response = requests.post("http://localhost:8000/item", json=item)
        if response.status_code == 201:
            item_id = response.json()["id"]
            # создать корзину
            cart_response = requests.post("http://localhost:8000/cart")
            if cart_response.status_code == 201:
                cart_id = cart_response.json()["id"]
                # добавить товар в корзину
                requests.post(f"http://localhost:8000/cart/{cart_id}/add/{item_id}")


def get_carts():
    for _ in range(100):  # запрашиваем корзины
        cart_id = faker.random_int(min=1, max=100)
        requests.get(f"http://localhost:8000/cart/{cart_id}")


def test_errors():
    for _ in range(100):  # 100 запросов для генерации ошибок
        requests.get("http://localhost:8000/test-error")


with ThreadPoolExecutor() as executor:  # параллельные запросы
    executor.submit(create_carts_and_items)
    executor.submit(get_carts)
    executor.submit(test_errors)
