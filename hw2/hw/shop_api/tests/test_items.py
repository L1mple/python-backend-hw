from fastapi.testclient import TestClient
from shop_api.main import app  

client = TestClient(app)

def test_item_root():
    response = client.get("/item/")
    assert response.status_code == 200


def test_create_item(sample_item_data):
    response = client.post("/item/", json=sample_item_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_item_data["name"]
    assert data["price"] == sample_item_data["price"]
    assert data["deleted"] is False
    assert "id" in data


def test_get_item(sample_item_data):
    # Сначала создаем товар
    create_response = client.post("/item/", json=sample_item_data)
    item_id = create_response.json()["id"]
    
    # Затем получаем его
    response = client.get(f"/item/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["name"] == sample_item_data["name"]

    # Получаем несуществующий товар
    response = client.get("/item/99999999")
    assert response.status_code == 404


def test_get_items_with_filters():
    # Создаем несколько товаров
    client.post("/item/", json={"name": "Item 1", "price": 50.0, "deleted": False})
    client.post("/item/", json={"name": "Item 2", "price": 150.0, "deleted": False})
    client.post("/item/", json={"name": "Item 3", "price": 200.0, "deleted": False})
    
    # Тестируем фильтрацию по цене
    response = client.get("/item/?min_price=100&max_price=200")
    assert response.status_code == 200
    data = response.json()
    assert all(100 <= item["price"] <= 200 for item in data)


def test_update_item(sample_item_data):
    # Создаем товар
    create_response = client.post("/item/", json=sample_item_data)
    item_id = create_response.json()["id"]
    
    # Обновляем товар
    update_data = {"name": "Updated Item", "price": 200.0, "deleted": False}
    response = client.put(f"/item/{item_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Item"
    assert data["price"] == 200.0

    # Обновляем несуществующий товар
    response = client.put("/item/99999999", json=update_data)
    assert response.status_code == 304


def test_patch_item(sample_item_data):
    # Создаем товар
    create_response = client.post("/item/", json=sample_item_data)
    item_id = create_response.json()["id"]
    
    # Обновляем товар
    patch_data = {"name": "Patched Item"}
    response = client.patch(f"/item/{item_id}", json=patch_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Patched Item"
    assert data["price"] == 100.0

    # Обновляем цену
    patch_data = {"price": 1.1}
    response = client.patch(f"/item/{item_id}", json=patch_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Patched Item"
    assert data["price"] == 1.1

    # Обновляем несуществующий товар
    response = client.patch("/item/99999999", json=patch_data)
    assert response.status_code == 304


def test_delete_item(sample_item_data):
    # Создаем товар
    create_response = client.post("/item/", json=sample_item_data)
    item_id = create_response.json()["id"]
    
    # Удаляем товар (мягкое удаление)
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 200
    
    # Проверяем, что товар помечен как удаленный
    get_response = client.get(f"/item/{item_id}")
    assert get_response.json()["deleted"] is True