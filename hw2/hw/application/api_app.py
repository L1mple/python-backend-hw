import os

from hw2.hw.shop_api.main import app
from grpc_client import create_cart_via_grpc
import json

root = os.path.dirname(os.path.abspath(__file__))
@app.post("/cart")
def create_cart():
    cart_id = create_cart_via_grpc()
    return {
        "id": cart_id,
        "items": [],
        "price": 0.0
    }

# Остальные эндпоинты для тестов
@app.get("/cart/{cart_id}")
def get_cart(cart_id: int):
    # Читаем из JSON файла
    try:
        with open(f"{root}carts.json", "r") as f:
            carts = json.load(f)
        return carts.get(str(cart_id), {"id": cart_id, "items": [], "price": 0.0})
    except:
        return {"id": cart_id, "items": [], "price": 0.0}

@app.post("/item")
def create_item(item: dict):
    # Заглушка для товаров
    return {"id": 1, **item, "deleted": False}

@app.get("/item/{item_id}")
def get_item(item_id: int):
    return {"id": item_id, "name": "Test", "price": 10.0, "deleted": False}





