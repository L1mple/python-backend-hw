from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from faker import Faker

faker = Faker()


def create_items():
    """Создает товары в магазине"""
    for _ in range(500):
        product_name = faker.word().capitalize() + " " + faker.word()
        price = round(faker.random.uniform(10.0, 9999.99), 2)
        
        response = requests.post(
            "http://localhost:8080/item",
            json={
                "name": product_name,
                "price": price,
            },
        )
        print(f"Create item: {response.status_code}")


def get_items():
    """Получает список товаров"""
    for _ in range(500):
        offset = faker.random_int(0, 50)
        limit = faker.random_int(5, 50)
        
        response = requests.get(
            "http://localhost:8080/item",
            params={
                "offset": offset,
                "limit": limit,
            },
        )
        print(f"Get items: {response.status_code}")


def get_item_by_id():
    """Получает товар по ID"""
    for _ in range(500):
        item_id = faker.random_int(1, 100)
        
        response = requests.get(
            f"http://localhost:8080/item/{item_id}",
        )
        print(f"Get item {item_id}: {response.status_code}")


def update_items():
    """Обновляет товары"""
    for _ in range(300):
        item_id = faker.random_int(1, 50)
        product_name = faker.word().capitalize() + " Updated"
        price = round(faker.random.uniform(10.0, 9999.99), 2)
        
        response = requests.put(
            f"http://localhost:8080/item/{item_id}",
            json={
                "name": product_name,
                "price": price,
            },
        )
        print(f"Update item {item_id}: {response.status_code}")


def create_carts():
    """Создает корзины"""
    for _ in range(300):
        response = requests.post(
            "http://localhost:8080/cart",
        )
        print(f"Create cart: {response.status_code}")


def get_carts():
    """Получает список корзин"""
    for _ in range(300):
        offset = faker.random_int(0, 50)
        limit = faker.random_int(5, 30)
        
        response = requests.get(
            "http://localhost:8080/cart",
            params={
                "offset": offset,
                "limit": limit,
            },
        )
        print(f"Get carts: {response.status_code}")


def add_items_to_cart():
    """Добавляет товары в корзины"""
    for _ in range(400):
        cart_id = faker.random_int(1, 100)
        item_id = faker.random_int(1, 100)
        
        response = requests.post(
            f"http://localhost:8080/cart/{cart_id}/add/{item_id}",
        )
        print(f"Add item {item_id} to cart {cart_id}: {response.status_code}")


def get_cart_by_id():
    """Получает корзину по ID"""
    for _ in range(400):
        cart_id = faker.random_int(1, 100)
        
        response = requests.get(
            f"http://localhost:8080/cart/{cart_id}",
        )
        print(f"Get cart {cart_id}: {response.status_code}")


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {}

        # Создание товаров
        for i in range(10):
            futures[executor.submit(create_items)] = f"create-items-{i}"

        # Получение списков товаров
        for i in range(10):
            futures[executor.submit(get_items)] = f"get-items-{i}"

        # Получение товаров по ID
        for i in range(10):
            futures[executor.submit(get_item_by_id)] = f"get-item-by-id-{i}"

        # Обновление товаров
        for i in range(5):
            futures[executor.submit(update_items)] = f"update-items-{i}"

        # Создание корзин
        for i in range(8):
            futures[executor.submit(create_carts)] = f"create-carts-{i}"

        # Получение списков корзин
        for i in range(8):
            futures[executor.submit(get_carts)] = f"get-carts-{i}"

        # Добавление товаров в корзины
        for i in range(12):
            futures[executor.submit(add_items_to_cart)] = f"add-items-to-cart-{i}"

        # Получение корзин по ID
        for i in range(12):
            futures[executor.submit(get_cart_by_id)] = f"get-cart-by-id-{i}"

        for future in as_completed(futures):
            print(f"✓ Completed {futures[future]}")

    print("\n🎯 DDoS test completed!")

