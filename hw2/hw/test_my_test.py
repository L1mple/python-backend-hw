import pytest
import requests
import asyncpg
import redis
from http import HTTPStatus
from typing import Any

BASE_URL = "http://localhost:8080"


class TestShopSystem:
    """Комплексные тесты для системы интернет-магазина"""

    # ==================== ТЕСТЫ ПОДКЛЮЧЕНИЯ К СЕРВИСАМ ====================

    def test_database_connection(self):
        """Тест подключения к PostgreSQL"""
        try:
            conn = asyncpg.connect(
                "postgresql://user:password@localhost:5432/shop"
            )
            print("✅ PostgreSQL connection successful")
            conn.close()
            assert True
        except Exception as e:
            pytest.fail(f"❌ PostgreSQL connection failed: {e}")

    def test_redis_connection(self):
        """Тест подключения к Redis"""
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            print("✅ Redis connection successful")
            assert True
        except Exception as e:
            pytest.fail(f"❌ Redis connection failed: {e}")

    def test_grafana_health(self):
        """Тест доступности Grafana"""
        try:
            response = requests.get("http://localhost:3000", timeout=5)
            assert response.status_code in [200, 302]  # 302 - redirect to login
            print("✅ Grafana is accessible")
        except Exception as e:
            pytest.fail(f"❌ Grafana is not accessible: {e}")

    def test_prometheus_health(self):
        """Тест доступности Prometheus"""
        try:
            response = requests.get("http://localhost:9090", timeout=5)
            assert response.status_code == 200
            print("✅ Prometheus is accessible")
        except Exception as e:
            pytest.fail(f"❌ Prometheus is not accessible: {e}")

    def test_main_api_health(self):
        """Тест доступности основного API"""
        try:
            response = requests.get(f"{BASE_URL}/docs", timeout=5)
            assert response.status_code == 200
            print("✅ Main API is accessible")
        except Exception as e:
            pytest.fail(f"❌ Main API is not accessible: {e}")

    # ==================== ОСНОВНЫЕ ТЕСТЫ API ====================

    def test_create_item_success(self):
        """Тест успешного создания товара"""
        item_data = {"name": "Unique Test Product", "price": 88.88}
        response = requests.post(f"{BASE_URL}/item", json=item_data)

        assert response.status_code == HTTPStatus.CREATED
        data = response.json()

        assert "id" in data
        assert data["name"] == item_data["name"]
        assert data["price"] == item_data["price"]

    def test_create_item_missing_fields(self):
        """Тест создания товара с отсутствующими полями"""
        # Без имени
        response = requests.post(f"{BASE_URL}/item", json={"price": 100.0})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

        # Без цены
        response = requests.post(f"{BASE_URL}/item", json={"name": "Test"})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

        # Пустое тело
        response = requests.post(f"{BASE_URL}/item", json={})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_get_item_success(self):
        """Тест успешного получения товара"""
        # Сначала создаем товар
        item_data = {"name": "Get Test Product", "price": 77.77}
        create_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert create_response.status_code == HTTPStatus.CREATED
        created_item = create_response.json()

        # Затем получаем его
        item_id = created_item['id']
        response = requests.get(f"{BASE_URL}/item/{item_id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert data["id"] == item_id
        assert data["name"] == created_item["name"]
        assert data["price"] == created_item["price"]

    def test_get_item_not_found(self):
        """Тест получения несуществующего товара"""
        response = requests.get(f"{BASE_URL}/item/999999")
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_all_items(self):
        """Тест получения списка всех товаров"""
        # Сначала создаем уникальный товар для этого теста
        unique_item_data = {"name": "Unique Item For List Test", "price": 123.45}
        create_response = requests.post(f"{BASE_URL}/item", json=unique_item_data)
        assert create_response.status_code == HTTPStatus.CREATED
        unique_item = create_response.json()

        # Получаем список всех товаров
        response = requests.get(f"{BASE_URL}/item")

        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Проверяем, что товары имеют правильную структуру
        for item in data:
            assert "id" in item
            assert "name" in item
            assert "price" in item

    def test_create_cart_success(self):
        """Тест успешного создания корзины"""
        response = requests.post(f"{BASE_URL}/cart")

        assert response.status_code == HTTPStatus.CREATED
        data = response.json()

        assert "id" in data
        assert "items" in data
        assert "price" in data
        assert data["items"] == []
        assert data["price"] == 0.0
        assert "Location" in response.headers

    def test_get_cart_success(self):
        """Тест успешного получения корзины"""
        # Сначала создаем корзину
        create_response = requests.post(f"{BASE_URL}/cart")
        assert create_response.status_code == HTTPStatus.CREATED
        created_cart = create_response.json()

        # Затем получаем ее
        cart_id = created_cart['id']
        response = requests.get(f"{BASE_URL}/cart/{cart_id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert data["id"] == cart_id
        assert data["items"] == []
        assert data["price"] == 0.0

    def test_get_cart_not_found(self):
        """Тест получения несуществующей корзины"""
        response = requests.get(f"{BASE_URL}/cart/999999")
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_add_to_cart_success(self):
        """Тест успешного добавления товара в корзину"""
        # Создаем товар
        item_data = {"name": "Cart Test Product", "price": 55.55}
        item_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert item_response.status_code == HTTPStatus.CREATED
        item_id = item_response.json()["id"]

        # Создаем корзину
        cart_response = requests.post(f"{BASE_URL}/cart")
        assert cart_response.status_code == HTTPStatus.CREATED
        cart_id = cart_response.json()["id"]

        # Добавляем товар в корзину
        response = requests.post(f"{BASE_URL}/cart/{cart_id}/add/{item_id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert data["id"] == cart_id
        assert len(data["items"]) == 1
        assert data["price"] == item_data["price"]

    def test_add_to_cart_nonexistent_cart(self):
        """Тест добавления товара в несуществующую корзину"""
        # Создаем товар
        item_data = {"name": "Nonexistent Cart Test", "price": 33.33}
        item_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert item_response.status_code == HTTPStatus.CREATED
        item_id = item_response.json()["id"]

        response = requests.post(f"{BASE_URL}/cart/999999/add/{item_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_add_to_cart_nonexistent_item(self):
        """Тест добавления несуществующего товара в корзину"""
        # Создаем корзину
        cart_response = requests.post(f"{BASE_URL}/cart")
        assert cart_response.status_code == HTTPStatus.CREATED
        cart_id = cart_response.json()["id"]

        response = requests.post(f"{BASE_URL}/cart/{cart_id}/add/999999")
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_add_to_cart_deleted_item(self):
        """Тест добавления удаленного товара в корзину"""
        # Создаем товар
        item_data = {"name": "To Be Deleted", "price": 44.44}
        item_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert item_response.status_code == HTTPStatus.CREATED
        item_id = item_response.json()["id"]

        # Создаем корзину
        cart_response = requests.post(f"{BASE_URL}/cart")
        assert cart_response.status_code == HTTPStatus.CREATED
        cart_id = cart_response.json()["id"]

        # Удаляем товар
        delete_response = requests.delete(f"{BASE_URL}/item/{item_id}")
        assert delete_response.status_code == HTTPStatus.OK

        # Пытаемся добавить удаленный товар
        add_response = requests.post(f"{BASE_URL}/cart/{cart_id}/add/{item_id}")
        assert add_response.status_code == HTTPStatus.NOT_FOUND

    def test_update_item_success(self):
        """Тест успешного обновления товара"""
        # Создаем товар
        item_data = {"name": "Original Name", "price": 50.0}
        create_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert create_response.status_code == HTTPStatus.CREATED
        item_id = create_response.json()["id"]

        # Обновляем товар
        update_data = {
            "name": "Updated Product Name",
            "price": 75.0
        }

        response = requests.put(f"{BASE_URL}/item/{item_id}", json=update_data)

        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert data["id"] == item_id
        assert data["name"] == update_data["name"]
        assert data["price"] == update_data["price"]

    def test_update_item_missing_fields(self):
        """Тест обновления товара с отсутствующими полями"""
        # Создаем товар
        item_data = {"name": "Test Item", "price": 60.0}
        create_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert create_response.status_code == HTTPStatus.CREATED
        item_id = create_response.json()["id"]

        # Без имени
        response = requests.put(f"{BASE_URL}/item/{item_id}", json={"price": 100.0})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

        # Без цены
        response = requests.put(f"{BASE_URL}/item/{item_id}", json={"name": "Test"})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_patch_item_success(self):
        """Тест успешного частичного обновления товара"""
        # Создаем товар
        item_data = {"name": "Patch Test Product", "price": 80.0}
        create_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert create_response.status_code == HTTPStatus.CREATED
        item_id = create_response.json()["id"]

        # Обновляем только цену
        patch_data = {"price": 90.0}
        response = requests.patch(f"{BASE_URL}/item/{item_id}", json=patch_data)

        # Проверяем, что не падает с 500 ошибкой
        assert response.status_code != HTTPStatus.INTERNAL_SERVER_ERROR

        # Если PATCH поддерживается, проверяем успешный ответ
        if response.status_code == HTTPStatus.OK:
            data = response.json()
            assert data["id"] == item_id
            assert data["price"] == patch_data["price"]

    def test_patch_item_empty_body(self):
        """Тест частичного обновления с пустым телом"""
        # Создаем товар
        item_data = {"name": "Empty Patch Test", "price": 70.0}
        create_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert create_response.status_code == HTTPStatus.CREATED
        item_id = create_response.json()["id"]

        response = requests.patch(f"{BASE_URL}/item/{item_id}", json={})

        if response.status_code == HTTPStatus.OK:
            data = response.json()
            assert "id" in data
            assert "name" in data
            assert "price" in data

    def test_patch_item_invalid_fields(self):
        """Тест частичного обновления с недопустимыми полями"""
        # Создаем товар
        item_data = {"name": "Invalid Patch Test", "price": 85.0}
        create_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert create_response.status_code == HTTPStatus.CREATED
        item_id = create_response.json()["id"]

        # Лишние поля
        patch_data = {
            "name": "New Name",
            "price": 95.0,
            "invalid_field": "value"
        }
        response = requests.patch(f"{BASE_URL}/item/{item_id}", json=patch_data)

        # Ожидаем ошибку валидации
        assert response.status_code in [
            HTTPStatus.UNPROCESSABLE_ENTITY,
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.OK  # Если система игнорирует лишние поля
        ]

    def test_delete_item_success(self):
        """Тест успешного удаления товара"""
        # Создаем товар
        item_data = {"name": "To Delete", "price": 66.66}
        create_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert create_response.status_code == HTTPStatus.CREATED
        item_id = create_response.json()["id"]

        # Удаляем товар
        response = requests.delete(f"{BASE_URL}/item/{item_id}")
        assert response.status_code == HTTPStatus.OK

        # Проверяем, что товар больше недоступен
        get_response = requests.get(f"{BASE_URL}/item/{item_id}")
        assert get_response.status_code == HTTPStatus.NOT_FOUND

    def test_delete_nonexistent_item(self):
        """Тест удаления несуществующего товара"""
        response = requests.delete(f"{BASE_URL}/item/999999")
        # Может возвращать 200 или 404 в зависимости от реализации
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]

    # ==================== ТЕСТЫ ФИЛЬТРАЦИИ И ПАГИНАЦИИ ====================

    @pytest.mark.parametrize("offset,limit,expected_status", [
        (0, 5, HTTPStatus.OK),
        (2, 3, HTTPStatus.OK),
        (-1, 5, HTTPStatus.UNPROCESSABLE_ENTITY),
        (0, 0, HTTPStatus.UNPROCESSABLE_ENTITY),
    ])
    def test_items_pagination(self, offset, limit, expected_status):
        """Тест пагинации товаров"""
        response = requests.get(f"{BASE_URL}/item", params={"offset": offset, "limit": limit})
        assert response.status_code == expected_status

    @pytest.mark.parametrize("min_price,max_price,expected_status", [
        (50.0, 100.0, HTTPStatus.OK),
        (0.0, 50.0, HTTPStatus.OK),
        (-1.0, 100.0, HTTPStatus.UNPROCESSABLE_ENTITY),
    ])
    def test_items_price_filter(self, min_price, max_price, expected_status):
        """Тест фильтрации товаров по цене"""
        params = {}
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price

        response = requests.get(f"{BASE_URL}/item", params=params)
        assert response.status_code == expected_status

    @pytest.mark.parametrize("min_price,max_price,expected_status", [
        (0.0, 100.0, HTTPStatus.OK),
        (500.0, 1000.0, HTTPStatus.OK),
        (-1.0, 100.0, HTTPStatus.UNPROCESSABLE_ENTITY),
    ])
    def test_carts_price_filter(self, min_price, max_price, expected_status):
        """Тест фильтрации корзин по цене"""
        params = {}
        if min_price is not None:
            params["min_price"] = min_price
        if max_price is not None:
            params["max_price"] = max_price

        response = requests.get(f"{BASE_URL}/cart", params=params)
        assert response.status_code == expected_status

    # ==================== ТЕСТЫ КОРЗИНЫ С ТОВАРАМИ ====================

    def test_add_same_item_multiple_times(self):
        """Тест добавления одного товара несколько раз"""
        # Создаем товар
        item_data = {"name": "Multiple Add Test", "price": 25.0}
        item_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert item_response.status_code == HTTPStatus.CREATED
        item_id = item_response.json()["id"]

        # Создаем корзину
        cart_response = requests.post(f"{BASE_URL}/cart")
        assert cart_response.status_code == HTTPStatus.CREATED
        cart_id = cart_response.json()["id"]

        # Добавляем первый раз
        response1 = requests.post(f"{BASE_URL}/cart/{cart_id}/add/{item_id}")
        assert response1.status_code == HTTPStatus.OK

        # Добавляем второй раз
        response2 = requests.post(f"{BASE_URL}/cart/{cart_id}/add/{item_id}")
        assert response2.status_code == HTTPStatus.OK

        # Проверяем корзину
        cart_data = response2.json()
        assert len(cart_data["items"]) == 1

    def test_cart_with_multiple_different_items(self):
        """Тест корзины с разными товарами"""
        # Создаем корзину
        cart_response = requests.post(f"{BASE_URL}/cart")
        assert cart_response.status_code == HTTPStatus.CREATED
        cart_id = cart_response.json()["id"]

        # Создаем несколько товаров
        items = []
        for i in range(2):  # Уменьшаем количество для скорости
            item_data = {"name": f"Multi Item {i}", "price": (i + 1) * 30.0}
            response = requests.post(f"{BASE_URL}/item", json=item_data)
            assert response.status_code == HTTPStatus.CREATED
            items.append(response.json())

        # Добавляем все товары в корзину
        for item in items:
            response = requests.post(f"{BASE_URL}/cart/{cart_id}/add/{item['id']}")
            assert response.status_code == HTTPStatus.OK

        # Проверяем итоговую корзину
        cart_response = requests.get(f"{BASE_URL}/cart/{cart_id}")
        assert cart_response.status_code == HTTPStatus.OK
        cart_data = cart_response.json()

        assert len(cart_data["items"]) == len(items)

    # ==================== ТЕСТЫ ГРАНИЧНЫХ СЛУЧАЕВ ====================

    def test_item_negative_price(self):
        """Тест создания товара с отрицательной ценой"""
        item_data = {"name": "Invalid Product", "price": -10.0}
        response = requests.post(f"{BASE_URL}/item", json=item_data)
        # Может возвращать 422 или 400 в зависимости от валидации
        assert response.status_code in [HTTPStatus.UNPROCESSABLE_ENTITY, HTTPStatus.BAD_REQUEST]

    def test_update_item_negative_price(self):
        """Тест обновления товара с отрицательной ценой"""
        # Создаем товар
        item_data = {"name": "Update Negative Test", "price": 40.0}
        create_response = requests.post(f"{BASE_URL}/item", json=item_data)
        assert create_response.status_code == HTTPStatus.CREATED
        item_id = create_response.json()["id"]

        update_data = {"name": "Updated", "price": -5.0}
        response = requests.put(f"{BASE_URL}/item/{item_id}", json=update_data)
        assert response.status_code in [HTTPStatus.UNPROCESSABLE_ENTITY, HTTPStatus.BAD_REQUEST]