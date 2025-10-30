import requests
import time
import random

BASE_URL = "http://localhost:8000"

endpoints = [
    "/health",
    "/item", 
    "/cart",
    "/metrics"
]

while True:
    try:
        # Случайный эндпоинт
        endpoint = random.choice(endpoints)
        url = BASE_URL + endpoint
        
        # Случайная задержка между запросами (1-10 секунд)
        delay = random.uniform(1, 10)
        
        # Делаем запрос
        response = requests.get(url, timeout=5)
        print(f"Request to {endpoint}: Status {response.status_code}")
        
        # Иногда создаем корзину и товары
        if random.random() < 0.1:  # 10% chance
            item_data = {"name": f"test_item_{random.randint(1,100)}", "price": round(random.uniform(10, 100), 2)}
            requests.post(BASE_URL + "/item", json=item_data)
            print("Created item")
            
        time.sleep(delay)
        
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
