def test_create_item(client):
    response = client.post("/item", json={"name": "Test Item", "price": 10.0})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["price"] == 10.0
    assert "id" in data


def test_get_item(client):
    response = client.post("/item", json={"name": "Get Test", "price": 15.0})
    item_id = response.json()["id"]

    response = client.get(f"/item/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Get Test"
    assert data["price"] == 15.0


def test_get_nonexistent_item(client):
    response = client.get("/item/999999")
    assert response.status_code == 404


def test_get_items_pagination(client):
    for i in range(15):
        client.post("/item", json={"name": f"Item {i}", "price": float(i + 1)})

    # Тестируем пагинацию
    response = client.get("/item?offset=0&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5

    response = client.get("/item?offset=5&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5


def test_get_items_with_filters(client):
    client.post("/item", json={"name": "Cheap", "price": 5.0})
    client.post("/item", json={"name": "Expensive", "price": 20.0})

    response = client.get("/item?min_price=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Expensive"

    response = client.get("/item?max_price=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Cheap"


def test_get_items_show_deleted(client, db_session):
    response = client.post("/item", json={"name": "To Delete", "price": 10.0})
    item_id = response.json()["id"]

    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 200

    response = client.get(f"/item/{item_id}")
    assert response.status_code == 404

    response = client.get("/item?show_deleted=true")
    assert response.status_code == 200
    data = response.json()


def test_update_item(client, db_session):
    response = client.post("/item", json={"name": "Original", "price": 10.0})
    item_id = response.json()["id"]

    response = client.put(f"/item/{item_id}", json={"name": "Updated", "price": 20.0})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["price"] == 20.0


def test_update_nonexistent_item(client):
    response = client.put("/item/999999", json={"name": "Updated", "price": 20.0})
    assert response.status_code == 404


def test_partial_update_item(client):
    response = client.post("/item", json={"name": "Original", "price": 10.0})
    item_id = response.json()["id"]

    response = client.patch(f"/item/{item_id}", json={"name": "Partially Updated"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Partially Updated"
    assert data["price"] == 10.0


def test_partial_update_nonexistent_item(client):
    response = client.patch("/item/999999", json={"name": "Updated"})
    assert response.status_code == 404


def test_partial_update_deleted_item(client):
    response = client.post("/item", json={"name": "ToDelete", "price": 10.0})
    item_id = response.json()["id"]

    client.delete(f"/item/{item_id}")

    response = client.patch(f"/item/{item_id}", json={"name": "New Name"})
    assert response.status_code == 304


def test_delete_item(client):
    # Создаем элемент
    response = client.post("/item", json={"name": "ToDelete", "price": 10.0})
    item_id = response.json()["id"]

    # Удаляем его
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Item deleted successfully"

    # Проверяем, что он больше не доступен
    response = client.get(f"/item/{item_id}")
    assert response.status_code == 404


def test_delete_nonexistent_item(client):
    response = client.delete("/item/999999")
    assert response.status_code == 404


def test_validation_errors_items(client):
    # Тестирование ошибок валидации параметров
    response = client.get("/item?offset=-1")
    assert response.status_code == 422

    response = client.get("/item?limit=0")
    assert response.status_code == 422

    response = client.get("/item?min_price=-1")
    assert response.status_code == 422

    response = client.get("/item?max_price=-1")
    assert response.status_code == 422


def test_extra_fields_forbidden_in_patch(client):
    response = client.post("/item", json={"name": "Test", "price": 10.0})
    item_id = response.json()["id"]
    response = client.patch(
        f"/item/{item_id}", json={"name": "Updated", "extra_field": "value"}
    )
    assert response.status_code == 422


def test_get_items_empty_database(client):
    response = client.get("/item")
    assert response.status_code == 200
    assert response.json() == []


def test_get_items_with_both_price_filters(client):
    client.post("/item", json={"name": "Item1", "price": 5.0})
    client.post("/item", json={"name": "Item2", "price": 15.0})
    client.post("/item", json={"name": "Item3", "price": 25.0})

    response = client.get("/item?min_price=10&max_price=20")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Item2"


def test_update_item_same_values(client):
    response = client.post("/item", json={"name": "Test", "price": 10.0})
    item_id = response.json()["id"]

    response = client.put(f"/item/{item_id}", json={"name": "Test", "price": 10.0})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test"
    assert data["price"] == 10.0


def test_partial_update_only_price(client):
    response = client.post("/item", json={"name": "Original", "price": 10.0})
    item_id = response.json()["id"]

    response = client.patch(f"/item/{item_id}", json={"price": 20.0})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Original"
    assert data["price"] == 20.0


def test_delete_already_deleted_item(client):
    response = client.post("/item", json={"name": "ToDelete", "price": 10.0})
    item_id = response.json()["id"]

    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 200

    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 404
