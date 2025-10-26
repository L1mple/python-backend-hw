from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytest
from faker import Faker
from fastapi.testclient import TestClient

from hw2.hw.shop_api import main

client = TestClient(main.app)
faker = Faker()


class TestCartEndpoints:
    """Тесты для эндпоинтов корзин"""
    
    @pytest.fixture()
    def empty_cart(self) -> dict[str, Any]:
        """Создает пустую корзину"""
        response = client.post("/cart")
        assert response.status_code == HTTPStatus.CREATED
        return response.json()
    
    @pytest.fixture()
    def cart_with_items(self, empty_cart: dict[str, Any], sample_items: list[dict]) -> dict[str, Any]:
        """Создает корзину с товарами"""
        cart_id = empty_cart["id"]
        # Добавляем 3 случайных товара
        for item in sample_items[:3]:
            client.post(f"/cart/{cart_id}/add/{item['id']}")
        return empty_cart
    
    @pytest.fixture(scope="session")
    def sample_items(self) -> list[dict]:
        """Создает тестовые товары"""
        items = []
        for i in range(5):
            item_data = {
                "name": f"Тестовый товар {i+1}",
                "price": faker.pyfloat(positive=True, min_value=10.0, max_value=100.0),
            }
            response = client.post("/item", json=item_data)
            assert response.status_code == HTTPStatus.CREATED
            items.append(response.json())
        return items

    def test_create_cart(self):
        """Тест создания корзины"""
        response = client.post("/cart")
        
        assert response.status_code == HTTPStatus.CREATED
        assert "location" in response.headers
        data = response.json()
        assert "id" in data
        assert isinstance(data["id"], int)


    @pytest.mark.parametrize("cart_fixture, expected_items_count", [
        ("empty_cart", 0),
        ("cart_with_items", 3),
    ])
    def test_get_cart(self, request, cart_fixture: str, expected_items_count: int):
        """Тест получения корзины"""
        cart = request.getfixturevalue(cart_fixture)
        cart_id = cart["id"]
        
        response = client.get(f"/cart/{cart_id}")
        
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data["items"]) == expected_items_count
        assert data["price"] >= 0  # Цена не может быть отрицательной
        
        # Проверяем расчет общей стоимости
        if expected_items_count > 0:
            total_price = sum(
                item["price"] * item["quantity"] 
                for item in data["items"]
            )
            assert data["price"] == pytest.approx(total_price, 1e-8)
        else:
            assert data["price"] == 0.0

    def test_get_nonexistent_cart(self):
        """Тест получения несуществующей корзины"""
        response = client.get(f"/cart/999999")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.parametrize("params, expected_status", [
        # Валидные параметры
        ({}, HTTPStatus.OK),
        ({"offset": 0, "limit": 10}, HTTPStatus.OK),
        ({"min_price": 50.0}, HTTPStatus.OK),
        ({"max_price": 100.0}, HTTPStatus.OK),
        ({"min_quantity": 1}, HTTPStatus.OK),
        ({"max_quantity": 5}, HTTPStatus.OK),
        
        # Невалидные параметры
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_quantity": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ])
    def test_get_carts_list(self, params: dict[str, Any], expected_status: int):
        """Тест получения списка корзин с фильтрацией"""
        response = client.get("/cart", params=params)
        
        assert response.status_code == expected_status
        
        if expected_status == HTTPStatus.OK:
            data = response.json()
            assert isinstance(data, list)
            
            # Проверяем фильтры
            if "min_price" in params:
                assert all(cart["price"] >= params["min_price"] for cart in data)
            if "max_price" in params:
                assert all(cart["price"] <= params["max_price"] for cart in data)


class TestItemEndpoints:
    """Тесты для эндпоинтов товаров"""
    
    @pytest.fixture()
    def sample_item(self) -> dict[str, Any]:
        """Создает тестовый товар"""
        item_data = {
            "name": f"Тестовый товар {uuid4().hex[:8]}",
            "price": faker.pyfloat(min_value=10.0, max_value=100.0),
        }
        response = client.post("/item", json=item_data)
        assert response.status_code == HTTPStatus.CREATED
        return response.json()
    
    @pytest.fixture()
    def deleted_item(self, sample_item: dict[str, Any]) -> dict[str, Any]:
        """Создает удаленный товар"""
        item_id = sample_item["id"]
        response = client.delete(f"/item/{item_id}")
        assert response.status_code == HTTPStatus.OK
        sample_item["deleted"] = True
        return sample_item

    def test_create_item(self):
        """Тест создания товара"""
        item_data = {
            "name": "Новый товар",
            "price": 29.99
        }
        
        response = client.post("/item", json=item_data)
        
        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert data["name"] == item_data["name"]
        assert data["price"] == item_data["price"]
        assert "id" in data
        assert data["deleted"] is False

    def test_create_item_invalid_data(self):
        """Тест создания товара с невалидными данными"""
        invalid_items = [
            {"name": "Только имя"},  # Нет цены
            {"price": 10.0},         # Нет имени
            {"name": "", "price": 10.0},  # Пустое имя
            {"name": "Товар", "price": -10.0},  # Отрицательная цена
        ]
        
        for invalid_item in invalid_items:
            response = client.post("/item", json=invalid_item)
            assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_get_item(self, sample_item: dict[str, Any]):
        """Тест получения товара"""
        item_id = sample_item["id"]
        
        response = client.get(f"/item/{item_id}")
        
        assert response.status_code == HTTPStatus.OK
        assert response.json() == sample_item

    def test_get_nonexistent_item(self):
        """Тест получения несуществующего товара"""
        response = client.get(f"/item/999999")
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_deleted_item(self, deleted_item: dict[str, Any]):
        """Тест получения удаленного товара"""
        item_id = deleted_item["id"]
        
        response = client.get(f"/item/{item_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.parametrize("params, expected_status", [
        # Валидные параметры
        ({"offset": 0, "limit": 5}, HTTPStatus.OK),
        ({"min_price": 20.0}, HTTPStatus.OK),
        ({"max_price": 50.0}, HTTPStatus.OK),
        ({"show_deleted": True}, HTTPStatus.OK),
        ({"show_deleted": False}, HTTPStatus.OK),
        
        # Невалидные параметры
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ])
    def test_get_items_list(self, params: dict[str, Any], expected_status: int):
        """Тест получения списка товаров с фильтрацией"""
        response = client.get("/item", params=params)
        
        assert response.status_code == expected_status
        
        if expected_status == HTTPStatus.OK:
            data = response.json()
            assert isinstance(data, list)
            
            # Проверяем фильтры
            if "min_price" in params:
                assert all(item["price"] >= params["min_price"] for item in data)
            if "max_price" in params:
                assert all(item["price"] <= params["max_price"] for item in data)
            if params.get("show_deleted") is False:
                assert all(item.get("deleted", False) is False for item in data)

    @pytest.mark.parametrize("update_data, expected_status", [
        ({"name": "Новое имя", "price": 99.99}, HTTPStatus.OK),
        ({"price": 15.50}, HTTPStatus.UNPROCESSABLE_ENTITY),  # Нет имени
        ({"name": "Только имя"}, HTTPStatus.UNPROCESSABLE_ENTITY),  # Нет цены
        ({}, HTTPStatus.UNPROCESSABLE_ENTITY),  # Пустые данные
    ])
    def test_full_update_item(
        self, 
        sample_item: dict[str, Any], 
        update_data: dict[str, Any], 
        expected_status: int
    ):
        """Тест полного обновления товара (PUT)"""
        item_id = sample_item["id"]
        
        response = client.put(f"/item/{item_id}", json=update_data)
        
        assert response.status_code == expected_status
        
        if expected_status == HTTPStatus.OK:
            updated_item = response.json()
            expected_item = sample_item.copy()
            expected_item.update(update_data)
            assert updated_item == expected_item

    def test_full_update_deleted_item(self, deleted_item: dict[str, Any]):
        """Тест полного обновления удаленного товара"""
        item_id = deleted_item["id"]
        
        response = client.put(
            f"/item/{item_id}", 
            json={"name": "Новое имя", "price": 99.99}
        )
        
        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.parametrize("item_fixture, patch_data, expected_status", [
        # Обновление существующего товара
        ("sample_item", {"name": "Частично обновлен"}, HTTPStatus.OK),
        ("sample_item", {"price": 77.77}, HTTPStatus.OK),
        ("sample_item", {"name": "Полное обновление", "price": 88.88}, HTTPStatus.OK),
        
        # Попытка обновления удаленного товара
        ("deleted_item", {"name": "Новое имя"}, HTTPStatus.NOT_MODIFIED),
        ("deleted_item", {"price": 99.99}, HTTPStatus.NOT_MODIFIED),
        
        # Невалидные данные
        ("sample_item", {"invalid_field": "value"}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ("sample_item", {"deleted": True}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ])
    def test_partial_update_item(
        self, 
        request, 
        item_fixture: str, 
        patch_data: dict[str, Any], 
        expected_status: int
    ):
        """Тест частичного обновления товара (PATCH)"""
        item_data: dict[str, Any] = request.getfixturevalue(item_fixture)
        item_id = item_data["id"]
        
        response = client.patch(f"/item/{item_id}", json=patch_data)
        
        assert response.status_code == expected_status
        
        if expected_status == HTTPStatus.OK:
            # Проверяем, что изменения применились
            updated_response = client.get(f"/item/{item_id}")
            assert updated_response.status_code == HTTPStatus.OK
            updated_item = updated_response.json()
            
            # Проверяем обновленные поля
            for key, value in patch_data.items():
                assert updated_item[key] == value

    def test_delete_item(self, sample_item: dict[str, Any]):
        """Тест удаления товара"""
        item_id = sample_item["id"]
        
        # Первое удаление
        response = client.delete(f"/item/{item_id}")
        assert response.status_code == HTTPStatus.OK
        
        # Проверяем, что товар не доступен
        response = client.get(f"/item/{item_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND
        
        # Повторное удаление (идемпотентность)
        response = client.delete(f"/item/{item_id}")
        assert response.status_code == HTTPStatus.OK

    def test_delete_nonexistent_item(self):
        """Тест удаления несуществующего товара"""
        response = client.delete(f"/item/999999")
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCartItemOperations:
    """Тесты операций с товарами в корзинах"""
    
    def test_add_item_to_cart(self, empty_cart: dict[str, Any], sample_item: dict[str, Any]):
        """Тест добавления товара в корзину"""
        cart_id = empty_cart["id"]
        item_id = sample_item["id"]
        
        response = client.post(f"/cart/{cart_id}/add/{item_id}")
        
        assert response.status_code == HTTPStatus.OK
        
        # Проверяем, что товар добавился
        cart_response = client.get(f"/cart/{cart_id}")
        cart_data = cart_response.json()
        
        assert any(item["id"] == item_id for item in cart_data["items"])
        assert cart_data["price"] == sample_item["price"]  # Один товар

    def test_add_nonexistent_item_to_cart(self, empty_cart: dict[str, Any]):
        """Тест добавления несуществующего товара в корзину"""
        cart_id = empty_cart["id"]
        
        response = client.post(f"/cart/{cart_id}/add/999999")
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_add_item_to_nonexistent_cart(self, sample_item: dict[str, Any]):
        """Тест добавления товара в несуществующую корзину"""
        item_id = sample_item["id"]
        
        response = client.post(f"/cart/999999/add/{item_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND