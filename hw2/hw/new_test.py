import pytest
from fastapi.testclient import TestClient
from shop_api.main import app
from shop_api.repositories import ItemRepository, CartRepository
from shop_api.database import get_connection
from shop_api.exceptions import ItemNotFoundError, ItemDeletedError

client = TestClient(app)

def test_patch_item_with_deleted_field():
    """Тест PATCH с полем deleted - должен вернуть 422"""
    # Создаем товар
    response = client.post("/item", json={"name": "Test Item", "price": 10.0})
    item_id = response.json()["id"]
    
    # Пытаемся обновить поле deleted
    response = client.patch(f"/item/{item_id}", json={"deleted": True})
    assert response.status_code == 422

def test_patch_item_with_extra_field():
    """Тест PATCH с лишним полем - должен вернуть 422"""
    # Создаем товар
    response = client.post("/item", json={"name": "Test Item", "price": 10.0})
    item_id = response.json()["id"]
    
    # Пытаемся добавить лишнее поле
    response = client.patch(f"/item/{item_id}", json={"name": "New Name", "extra_field": "value"})
    assert response.status_code == 422

def test_update_deleted_item():
    """Тест обновления удаленного товара - должен вернуть 304"""
    # Создаем товар
    response = client.post("/item", json={"name": "Test Item", "price": 10.0})
    item_id = response.json()["id"]
    
    # Удаляем товар
    client.delete(f"/item/{item_id}")
    
    # Пытаемся обновить удаленный товар
    response = client.put(f"/item/{item_id}", json={"name": "Updated", "price": 20.0})
    assert response.status_code == 304

def test_patch_deleted_item():
    """Тест PATCH удаленного товара - должен вернуть 304"""
    # Создаем товар
    response = client.post("/item", json={"name": "Test Item", "price": 10.0})
    item_id = response.json()["id"]
    
    # Удаляем товар
    client.delete(f"/item/{item_id}")
    
    # Пытаемся изменить удаленный товар
    response = client.patch(f"/item/{item_id}", json={"name": "Updated"})
    assert response.status_code == 304

def test_add_item_to_nonexistent_cart():
    """Тест добавления товара в несуществующую корзину"""
    # Создаем товар
    response = client.post("/item", json={"name": "Test Item", "price": 10.0})
    item_id = response.json()["id"]
    
    # Пытаемся добавить в несуществующую корзину
    response = client.post(f"/cart/99999/add/{item_id}")
    assert response.status_code == 404

def test_add_nonexistent_item_to_cart():
    """Тест добавления несуществующего товара в корзину"""
    # Создаем корзину
    response = client.post("/cart")
    cart_id = response.json()["id"]
    
    # Пытаемся добавить несуществующий товар
    response = client.post(f"/cart/{cart_id}/add/99999")
    assert response.status_code == 404

def test_add_deleted_item_to_cart():
    """Тест добавления удаленного товара в корзину"""
    # Создаем корзину
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]
    
    # Создаем товар
    item_response = client.post("/item", json={"name": "Test Item", "price": 10.0})
    item_id = item_response.json()["id"]
    
    # Удаляем товар
    client.delete(f"/item/{item_id}")
    
    # Пытаемся добавить удаленный товар в корзину
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 404

def test_get_nonexistent_cart():
    """Тест получения несуществующей корзины"""
    response = client.get("/cart/99999")
    assert response.status_code == 404

def test_get_nonexistent_item():
    """Тест получения несуществующего товара"""
    response = client.get("/item/99999")
    assert response.status_code == 404

def test_update_nonexistent_item():
    """Тест обновления несуществующего товара"""
    response = client.put("/item/99999", json={"name": "Test", "price": 10.0})
    assert response.status_code == 404

def test_patch_nonexistent_item():
    """Тест PATCH несуществующего товара"""
    response = client.patch("/item/99999", json={"name": "Test"})
    assert response.status_code == 404

def test_delete_nonexistent_item():
    """Тест удаления несуществующего товара"""
    response = client.delete("/item/99999")
    assert response.status_code == 404

def test_delete_already_deleted_item():
    """Тест удаления уже удаленного товара"""
    # Создаем товар
    response = client.post("/item", json={"name": "Test Item", "price": 10.0})
    item_id = response.json()["id"]
    
    # Удаляем товар дважды
    response1 = client.delete(f"/item/{item_id}")
    response2 = client.delete(f"/item/{item_id}")
    
    assert response1.status_code == 200
    assert response2.status_code == 200  # Должен быть идемпотентным

def test_patch_with_no_changes():
    """Тест PATCH без изменений"""
    # Создаем товар
    response = client.post("/item", json={"name": "Test Item", "price": 10.0})
    item_id = response.json()["id"]
    
    # PATCH без изменений
    response = client.patch(f"/item/{item_id}", json={})
    assert response.status_code == 200

def test_cart_with_deleted_items():
    """Тест корзины с удаленными товарами"""
    # Создаем корзину
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]
    
    # Создаем товар
    item_response = client.post("/item", json={"name": "Test Item", "price": 10.0})
    item_id = item_response.json()["id"]
    
    # Добавляем товар в корзину
    client.post(f"/cart/{cart_id}/add/{item_id}")
    
    # Удаляем товар
    client.delete(f"/item/{item_id}")
    
    # Получаем корзину - удаленный товар не должен отображаться
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    cart_data = response.json()
    assert len(cart_data["items"]) == 0  # Удаленные товары не показываются