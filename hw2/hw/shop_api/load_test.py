from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from faker import Faker
import random

faker = Faker()

BASE_URL = "http://localhost:8000"

def create_items():
    """Создание товаров"""
    for _ in range(100):
        item_data = {
            "name": faker.word().capitalize() + " " + faker.word(),
            "price": round(random.uniform(10.0, 1000.0), 2)
        }
        response = requests.post(f"{BASE_URL}/item", json=item_data)
        print(f"Created item: {response.status_code}")

def get_items():
    """Получение списка товаров"""
    for _ in range(100):
        params = {
            "offset": random.randint(0, 50),
            "limit": random.randint(5, 20),
            "min_price": random.choice([None, 50.0, 100.0]),
            "max_price": random.choice([None, 500.0, 800.0])
        }
        response = requests.get(f"{BASE_URL}/item", params=params)
        print(f"Get items: {response.status_code}")

def create_and_fill_carts():
    """Создание корзин и добавление товаров"""
    for _ in range(50):
        # Создаем корзину
        cart_response = requests.post(f"{BASE_URL}/cart")
        if cart_response.status_code == 201:
            cart_id = cart_response.json()["id"]
            
            # Добавляем случайные товары в корзину
            for _ in range(random.randint(1, 5)):
                item_id = random.randint(1, 50)
                add_response = requests.post(f"{BASE_URL}/cart/{cart_id}/add/{item_id}")
                print(f"Add item to cart: {add_response.status_code}")

def get_carts():
    """Получение списка корзин"""
    for _ in range(50):
        params = {
            "offset": random.randint(0, 10),
            "limit": random.randint(5, 15)
        }
        response = requests.get(f"{BASE_URL}/cart", params=params)
        print(f"Get carts: {response.status_code}")

def update_items():
    """Обновление товаров"""
    for _ in range(50):
        item_id = random.randint(1, 50)
        patch_data = {
            "price": round(random.uniform(10.0, 1000.0), 2)
        }
        response = requests.patch(f"{BASE_URL}/item/{item_id}", json=patch_data)
        print(f"Update item: {response.status_code}")

def delete_items():
    """Удаление товаров"""
    for _ in range(20):
        item_id = random.randint(1, 100)
        response = requests.delete(f"{BASE_URL}/item/{item_id}")
        print(f"Delete item: {response.status_code}")

if __name__ == "__main__":
    print("Starting load test...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {}
        
        # Создаем товары
        for i in range(3):
            futures[executor.submit(create_items)] = f"create-items-{i}"
        
        # Получаем товары
        for i in range(5):
            futures[executor.submit(get_items)] = f"get-items-{i}"
        
        # Создаем и заполняем корзины
        for i in range(3):
            futures[executor.submit(create_and_fill_carts)] = f"create-carts-{i}"
        
        # Получаем корзины
        for i in range(3):
            futures[executor.submit(get_carts)] = f"get-carts-{i}"
        
        # Обновляем товары
        for i in range(2):
            futures[executor.submit(update_items)] = f"update-items-{i}"
        
        # Удаляем товары
        futures[executor.submit(delete_items)] = "delete-items"
        
        for future in as_completed(futures):
            print(f"Completed: {futures[future]}")
    
    print("Load test completed!")