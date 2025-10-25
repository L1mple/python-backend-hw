from fastapi.testclient import TestClient
from shop_api.main import app  

client = TestClient(app)


def test_cart_root():
    response = client.get("/cart/?min_price=100&max_price=200&min_quantity=1&max_quantity=2")
    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_create_cart():
    response = client.post("/cart/")
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["items"] == []
    assert data["price"] == 0.0


def test_get_cart_by_id():
    cart_response = client.post("/cart/")
    assert cart_response.status_code == 201
    cart_id = cart_response.json()["id"]

    # Проверяем корзину
    cart_response = client.get(f"/cart/{cart_id}")
    cart_data = cart_response.json()
    assert cart_response.status_code == 200

    # Запрос несуществующей корзины
    cart_response = client.get("/cart/99999999")
    cart_data = cart_response.json()
    assert cart_response.status_code == 404


def test_add_item_to_cart(sample_item_data):
    # Создаем товар
    item_response = client.post("/item/", json=sample_item_data)
    item_id = item_response.json()["id"]
    
    # Создаем корзину
    cart_response = client.post("/cart/")
    cart_id = cart_response.json()["id"]
    
    # Добавляем товар в корзину
    add_response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert add_response.status_code == 201
    
    # Проверяем корзину
    cart_response = client.get(f"/cart/{cart_id}")
    cart_data = cart_response.json()
    
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["id"] == item_id
    assert cart_data["items"][0]["quantity"] == 1
    assert cart_data["price"] == sample_item_data["price"]

    # Добавляем тот же товар в ту же корзину
    add_response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert add_response.status_code == 201

    # Проверяем корзину
    cart_response = client.get(f"/cart/{cart_id}")
    cart_data = cart_response.json()

    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["id"] == item_id
    assert cart_data["items"][0]["quantity"] == 2
    assert cart_data["price"] == sample_item_data["price"] * 2

    # Запрос несуществующей корзины
    cart_response = client.post(f"/cart/9999999999/add/{item_id}")
    assert cart_response.status_code == 404


     # Запрос несуществующего товара
    cart_response = client.post(f"/cart/{cart_id}/add/999999999999")
    assert cart_response.status_code == 404

