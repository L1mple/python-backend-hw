import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException


class TestRoutersValidation:

    def test_get_carts_invalid_offset_limit(self, client):
        response = client.get("/cart/?offset=-1&limit=10")
        assert response.status_code == 422

        response = client.get("/cart/?offset=0&limit=0")
        assert response.status_code == 422

        response = client.get("/cart/?offset=0&limit=-5")
        assert response.status_code == 422

    def test_get_items_invalid_offset_limit(self, client):
        response = client.get("/item/?offset=-1&limit=10")
        assert response.status_code == 422

        response = client.get("/item/?offset=0&limit=0")
        assert response.status_code == 422

    def test_get_cart_not_found(self, client):
        response = client.get("/cart/999999")
        assert response.status_code == 404
        assert "Cart not found" in response.json()["detail"]

    def test_add_item_cart_not_found(self, client, create_test_items):
        # Несуществующая корзина
        response = client.post("/cart/999999/add/1")
        assert response.status_code == 404

    def test_add_item_item_not_found(self, client):
        # Создаем корзину, но добавляем несуществующий товар
        cart_response = client.post("/cart/")
        cart_id = cart_response.json()["id"]

        response = client.post(f"/cart/{cart_id}/add/999999")
        assert response.status_code == 404

    def test_get_item_not_found(self, client):
        response = client.get("/item/999999")
        assert response.status_code == 404
        assert "Item not found" in response.json()["detail"]

    def test_replace_item_not_found(self, client):
        response = client.put("/item/999999", json={"name": "Test", "price": 10.0})
        assert response.status_code == 404

    def test_update_item_not_found(self, client):
        response = client.patch("/item/999999", json={"name": "Updated"})
        assert response.status_code == 404

    def test_delete_item_not_found(self, client):
        response = client.delete("/item/999999")
        # Должен вернуть 200 даже если товара нет (идемпотентность)
        assert response.status_code == 200

    def test_update_deleted_item(self, client, create_test_items):
        # Сначала удаляем товар
        item_id = create_test_items[0]
        client.delete(f"/item/{item_id}")

        # Пытаемся обновить удаленный товар
        response = client.patch(f"/item/{item_id}", json={"price": 100.0})
        assert response.status_code == 304

    def test_create_cart_edge_cases(self, client):
        response = client.post("/cart/")
        assert response.status_code == 201
        assert "id" in response.json()
        # Проверяем заголовок Location
        assert "Location" in response.headers
        assert "/cart/" in response.headers["Location"]

    def test_get_carts_edge_cases(self, client):
        # Тест с различными фильтрами (убираем зависимость от фикстуры)
        response = client.get("/cart/?min_price=0&max_price=1000&min_quantity=0&max_quantity=100")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

        # Тест с большим offset
        response = client.get("/cart/?offset=1000&limit=10")
        assert response.status_code == 200
        assert response.json() == []

        # Тест с большим limit
        response = client.get("/cart/?offset=0&limit=1000")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_items_edge_cases(self, client, create_test_items):
        # Тест с show_deleted=True
        item_id = create_test_items[0]
        client.delete(f"/item/{item_id}")

        response = client.get("/item/?show_deleted=true")
        assert response.status_code == 200
        deleted_items = [item for item in response.json() if item["deleted"]]
        assert len(deleted_items) >= 1

        # Тест с фильтрами по цене
        response = client.get("/item/?min_price=50&max_price=100")
        assert response.status_code == 200
        for item in response.json():
            assert 50 <= item["price"] <= 100

        # Тест с offset превышающим количество
        response = client.get("/item/?offset=1000&limit=10")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_item_edge_cases(self, client):
        # Тест с минимальной ценой
        response = client.post("/item/", json={"name": "Min Price Item", "price": 0.01})
        assert response.status_code == 201
        assert response.json()["price"] == 0.01

        # Тест с очень длинным названием
        long_name = "A" * 100
        response = client.post("/item/", json={"name": long_name, "price": 10.0})
        assert response.status_code == 201
        assert response.json()["name"] == long_name

    def test_replace_item_edge_cases(self, client, create_test_items):
        item_id = create_test_items[0]

        # Тест с нулевой ценой
        response = client.put(f"/item/{item_id}", json={"name": "Zero Price", "price": 0.0})
        assert response.status_code == 200
        assert response.json()["price"] == 0.0

        # Тест с очень большой ценой
        response = client.put(f"/item/{item_id}", json={"name": "Expensive", "price": 999999.99})
        assert response.status_code == 200
        assert response.json()["price"] == 999999.99

    def test_update_item_edge_cases(self, client, create_test_items):
        item_id = create_test_items[0]

        # Тест обновления только цены
        response = client.patch(f"/item/{item_id}", json={"price": 888.88})
        assert response.status_code == 200
        assert response.json()["price"] == 888.88

        # Тест обновления только названия
        response = client.patch(f"/item/{item_id}", json={"name": "Only Name Updated"})
        assert response.status_code == 200
        assert response.json()["name"] == "Only Name Updated"

        # Тест с пустым телом запроса
        response = client.patch(f"/item/{item_id}", json={})
        assert response.status_code == 200

        # Тест с невалидными полями (должны игнорироваться)
        response = client.patch(f"/item/{item_id}", json={"invalid_field": "value", "price": 777.77})
        assert response.status_code == 200
        assert response.json()["price"] == 777.77

    def test_add_item_to_cart_edge_cases(self, client, create_test_items):
        # Сначала получаем информацию о товаре
        item_id = create_test_items[0]
        item_response = client.get(f"/item/{item_id}")
        assert item_response.status_code == 200
        item_data = item_response.json()
        item_name = item_data["name"]
        print(f"Testing with item: {item_name}")

        # Создаем корзину
        cart_response = client.post("/cart/")
        cart_id = cart_response.json()["id"]

        # Добавляем один товар несколько раз
        for i in range(3):
            response = client.post(f"/cart/{cart_id}/add/{item_id}")
            assert response.status_code == 200
            assert response.json()["status"] == "success"

        # Проверяем что корзина содержит товар
        cart_response = client.get(f"/cart/{cart_id}")
        assert cart_response.status_code == 200
        cart = cart_response.json()

        # Ищем товар по имени
        item = next((item for item in cart["items"] if item.get("name") == item_name), None)
        assert item is not None, f"Item '{item_name}' not found in cart"
        assert item["quantity"] == 3

    def test_cart_operations_sequence(self, client, create_test_items):
        # Создаем корзину
        cart_response = client.post("/cart/")
        cart_id = cart_response.json()["id"]

        # Добавляем несколько товаров
        for item_id in create_test_items[:3]:
            response = client.post(f"/cart/{cart_id}/add/{item_id}")
            assert response.status_code == 200

        # Получаем корзину и проверяем содержимое
        cart_response = client.get(f"/cart/{cart_id}")
        assert cart_response.status_code == 200
        cart = cart_response.json()
        assert len(cart["items"]) == 3
        assert cart["price"] > 0

        # Удаляем один товар
        item_to_delete = create_test_items[0]
        client.delete(f"/item/{item_to_delete}")

        # Снова получаем корзину - удаленный товар должен быть отмечен как unavailable
        cart_response = client.get(f"/cart/{cart_id}")
        assert cart_response.status_code == 200
        cart = cart_response.json()
        deleted_item = next((item for item in cart["items"] if not item["available"]), None)
        assert deleted_item is not None

    def test_get_cart_success(self, client, create_test_cart_with_items):
        cart_id = create_test_cart_with_items
        response = client.get(f"/cart/{cart_id}")
        assert response.status_code == 200
        assert response.json()["id"] == cart_id

    def test_add_item_to_cart_success(self, client, create_test_cart_with_items, create_test_items):
        cart_id = create_test_cart_with_items
        item_id = create_test_items[0]

        response = client.post(f"/cart/{cart_id}/add/{item_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_get_carts_success(self, client, create_test_carts_with_items):
        response = client.get("/cart/?offset=0&limit=10")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_cart_success(self, client):
        response = client.post("/cart/")
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        # Проверяем что Location header установлен
        assert "Location" in response.headers
        assert f"/cart/{data['id']}" in response.headers["Location"]

    def test_get_item_success(self, client, create_test_items):
        item_id = create_test_items[0]
        response = client.get(f"/item/{item_id}")
        assert response.status_code == 200
        assert response.json()["id"] == item_id

    def test_replace_item_success(self, client, create_test_items):
        item_id = create_test_items[0]
        response = client.put(
            f"/item/{item_id}",
            json={"name": "Updated Name", "price": 99.99}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["price"] == 99.99

    def test_update_item_success(self, client, create_test_items):
        item_id = create_test_items[0]
        response = client.patch(
            f"/item/{item_id}",
            json={"name": "Patched Name"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Patched Name"

    def test_delete_item_success(self, client, create_test_items):
        item_id = create_test_items[0]
        response = client.delete(f"/item/{item_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_update_deleted_item_304(self, client, create_test_items):
        item_id = create_test_items[0]
        # Сначала удаляем товар
        client.delete(f"/item/{item_id}")
        # Пытаемся обновить удаленный товар
        response = client.patch(f"/item/{item_id}", json={"name": "Should Fail"})
        assert response.status_code == 304

    def test_get_items_success(self, client, create_test_items):
        response = client.get("/item/?offset=0&limit=10")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
