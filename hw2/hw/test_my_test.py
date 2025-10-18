import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from http import HTTPStatus
import json
from decimal import Decimal

from .shop_api import main
from .shop_api.main import app
client = TestClient(app)

target = 'hw.shop_api.main'
class TestDatabaseHelpers:
    """Тесты вспомогательных функций базы данных"""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_db_connection(self):
        """Тест подключения к БД"""
        with patch(f'{target}.asyncpg.connect') as mock_connect, \
                patch.dict('os.environ', {}, clear=True):
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn

            connection = await main.get_db_connection()

            mock_connect.assert_called_once_with(
                database='shop',
                user='user',
                password='password',
                host='postgres',
                port='5432'
            )
            assert connection == mock_conn

    @pytest.mark.asyncio
    async def test_get_redis_connection(self):
        """Тест подключения к Redis"""
        with patch(f'{target}.redis.Redis') as mock_redis, \
                patch.dict('os.environ', {}, clear=True):

            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            connection = await main.get_redis_connection()

            mock_redis.assert_called_once_with(
                host='redis',
                port=6379,
                decode_responses=True
            )

    @pytest.mark.asyncio
    async def test_get_cart_from_db_success(self):
        """Тест получения корзины из БД - успешный случай"""
        mock_conn = AsyncMock()
        mock_cart = {
            'id': 1,
            'price': Decimal('100.50'),
            'created_at': None
        }
        mock_items = [
            {'product_id': 1, 'quantity': 2, 'price': Decimal('50.25')}
        ]

        mock_conn.fetchrow.return_value = mock_cart
        mock_conn.fetch.return_value = mock_items

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            result = await main.get_cart_from_db(1)

            expected = {
                'id': 1,
                'items': [{
                    'id': 1,
                    'quantity': 2,
                    'price': 50.25
                }],
                'price': 100.50,
                'created_at': None
            }
            assert result == expected

    @pytest.mark.asyncio
    async def test_get_cart_from_db_not_found(self):
        """Тест получения несуществующей корзины из БД"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            result = await main.get_cart_from_db(999)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_cart_with_cache_hit(self):
        """Тест получения корзины из кеша"""
        cached_cart = {
            'id': 1,
            'items': [{'id': 1, 'quantity': 1, 'price': 50.0}],
            'price': 50.0
        }

        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps(cached_cart)

        with patch(f'{target}.get_redis_connection', return_value=mock_redis):
            result = await main.get_cart_with_cache(1)

            assert result == cached_cart
            mock_redis.get.assert_called_once_with('cart:1')

    @pytest.mark.asyncio
    async def test_get_cart_with_cache_miss(self):
        """Тест получения корзины при промахе кеша"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        db_cart = {
            'id': 1,
            'items': [{'id': 1, 'quantity': 1, 'price': 50.0}],
            'price': 50.0
        }

        with patch(f'{target}.get_redis_connection', return_value=mock_redis), \
                patch(f'{target}.get_cart_from_db', return_value=db_cart):
            result = await main.get_cart_with_cache(1)

            assert result == db_cart
            mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_cart_cache(self):
        """Тест инвалидации кеша корзины"""
        mock_redis = AsyncMock()

        with patch(f'{target}.get_redis_connection', return_value=mock_redis):
            await main.invalidate_cart_cache(1)

            mock_redis.delete.assert_called_once_with('cart:1')

    @pytest.mark.asyncio
    async def test_get_item_from_db_success(self):
        """Тест получения товара из БД"""
        mock_conn = AsyncMock()
        mock_item = {
            'id': 1,
            'name': 'Test Item',
            'price': Decimal('99.99'),
            'deleted': False
        }
        mock_conn.fetchrow.return_value = mock_item

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            result = await main.get_item_from_db(1)

            expected = {
                'id': 1,
                'name': 'Test Item',
                'price': 99.99,
                'deleted': False
            }
            assert result == expected

    @pytest.mark.asyncio
    async def test_get_item_from_db_not_found(self):
        """Тест получения несуществующего товара из БД"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            result = await main.get_item_from_db(999)
            assert result is None


class TestRootEndpoint:
    """Тесты корневого эндпоинта"""

    def test_root(self):
        """Тест корневого эндпоинта"""
        response = client.get("/")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"status": "ok"}


class TestCartEndpoints:
    """Тесты эндпоинтов корзины"""

    @pytest.mark.asyncio
    async def test_create_cart_success(self):
        """Тест успешного создания корзины"""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.post("/cart")

            assert response.status_code == HTTPStatus.CREATED
            data = response.json()
            assert data['id'] == 1
            assert data['items'] == []
            assert data['price'] == 0.0
            assert 'Location' in response.headers

    @pytest.mark.asyncio
    async def test_create_cart_database_error(self):
        """Тест ошибки при создании корзины"""
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = Exception("DB error")

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.post("/cart")

            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Error creating cart" in response.json()['detail']

    @pytest.mark.asyncio
    async def test_get_cart_success(self):
        """Тест успешного получения корзины"""
        cart_data = {
            'id': 1,
            'items': [{'id': 1, 'quantity': 1, 'price': 50.0}],
            'price': 50.0
        }

        with patch(f'{target}.get_cart_with_cache', return_value=cart_data):
            response = client.get("/cart/1")

            assert response.status_code == HTTPStatus.OK
            assert response.json() == cart_data

    @pytest.mark.asyncio
    async def test_get_cart_not_found(self):
        """Тест получения несуществующей корзины"""
        with patch(f'{target}.get_cart_with_cache', return_value=None):
            response = client.get("/cart/999")

            assert response.status_code == HTTPStatus.NOT_FOUND
            assert "Cart not found" in response.json()['detail']

    @pytest.mark.asyncio
    async def test_get_carts_success(self):
        """Тест успешного получения списка корзин"""
        mock_conn = AsyncMock()
        mock_carts = [
            {'id': 1, 'price': Decimal('100.0'), 'created_at': None, 'total_quantity': 2},
            {'id': 2, 'price': Decimal('200.0'), 'created_at': None, 'total_quantity': 1}
        ]
        mock_items = [
            [{'product_id': 1, 'quantity': 2, 'price': Decimal('50.0')}],
            [{'product_id': 2, 'quantity': 1, 'price': Decimal('200.0')}]
        ]

        mock_conn.fetch.side_effect = [mock_carts] + mock_items

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/cart")

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert len(data) == 2
            assert data[0]['id'] == 1
            assert data[1]['id'] == 2

    @pytest.mark.asyncio
    async def test_get_carts_with_filters(self):
        """Тест получения корзин с фильтрами"""
        mock_conn = AsyncMock()
        mock_carts = [{'id': 1, 'price': Decimal('150.0'), 'created_at': None, 'total_quantity': 3}]
        mock_items = [[{'product_id': 1, 'quantity': 3, 'price': Decimal('50.0')}]]

        mock_conn.fetch.side_effect = [mock_carts] + mock_items

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/cart?min_price=100&max_price=200&min_quantity=2&max_quantity=5")

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert len(data) == 1

    @pytest.mark.asyncio
    async def test_get_carts_database_error(self):
        """Тест ошибки при получении списка корзин"""
        mock_conn = AsyncMock()
        mock_conn.fetch.side_effect = Exception("DB error")

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/cart")

            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Error getting carts" in response.json()['detail']


    @pytest.mark.asyncio
    async def test_add_to_cart_cart_not_found(self):
        """Тест добавления в несуществующую корзину"""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = None  # cart doesn't exist

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.post("/cart/999/add/1")

            assert response.status_code == HTTPStatus.NOT_FOUND
            assert "Cart not found" in response.json()['detail']

    @pytest.mark.asyncio
    async def test_add_to_cart_item_not_found(self):
        """Тест добавления несуществующего товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = True  # cart exists
        mock_conn.fetchrow.return_value = None  # item doesn't exist

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.post("/cart/1/add/999")

            assert response.status_code == HTTPStatus.NOT_FOUND
            assert "Item not found" in response.json()['detail']

    @pytest.mark.asyncio
    async def test_add_to_cart_database_error(self):
        """Тест ошибки при добавлении в корзину"""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = True
        mock_conn.fetchrow.side_effect = Exception("DB error")

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.post("/cart/1/add/1")

            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Error adding to cart" in response.json()['detail']

    @pytest.mark.asyncio
    async def test_add_to_cart_database_error(self):
        """Тест ошибки при добавлении в корзину"""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = True
        mock_conn.fetchrow.side_effect = Exception("DB error")

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.post("/cart/1/add/1")

            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Error adding to cart" in response.json()['detail']


class TestItemEndpoints:
    """Тесты эндпоинтов товаров"""

    @pytest.mark.asyncio
    async def test_get_item_success(self):
        """Тест успешного получения товара"""
        item_data = {
            'id': 1,
            'name': 'Test Item',
            'price': 99.99,
            'deleted': False
        }

        with patch(f'{target}.get_item_from_db', return_value=item_data):
            response = client.get("/item/1")

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert data['id'] == 1
            assert data['quantity'] == 1  # Добавлено для обратной совместимости

    @pytest.mark.asyncio
    async def test_get_item_not_found(self):
        """Тест получения несуществующего товара"""
        with patch(f'{target}.get_item_from_db', return_value=None):
            response = client.get("/item/999")

            assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_item_deleted(self):
        """Тест получения удаленного товара"""
        item_data = {
            'id': 1,
            'name': 'Deleted Item',
            'price': 99.99,
            'deleted': True
        }

        with patch(f'{target}.get_item_from_db', return_value=item_data):
            response = client.get("/item/1")

            assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_items_success(self):
        """Тест успешного получения списка товаров"""
        mock_conn = AsyncMock()
        mock_items = [
            {
                'id': 1,
                'name': 'Item 1',
                'price': Decimal('50.0'),
                'deleted': False,
                'created_at': None
            }
        ]
        mock_conn.fetch.return_value = mock_items

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/item")

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert len(data) == 1
            assert data[0]['name'] == 'Item 1'

    @pytest.mark.asyncio
    async def test_get_items_with_filters(self):
        """Тест получения товаров с фильтрами"""
        mock_conn = AsyncMock()
        mock_items = [
            {
                'id': 1,
                'name': 'Item 1',
                'price': Decimal('75.0'),
                'deleted': False,
                'created_at': None
            }
        ]
        mock_conn.fetch.return_value = mock_items

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/item?min_price=50&max_price=100&show_deleted=true&offset=0&limit=10")

            assert response.status_code == HTTPStatus.OK

    @pytest.mark.asyncio
    async def test_get_items_database_error(self):
        """Тест ошибки при получении списка товаров"""
        mock_conn = AsyncMock()
        mock_conn.fetch.side_effect = Exception("DB error")

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/item")

            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Error getting items" in response.json()['detail']

    @pytest.mark.asyncio
    async def test_create_item_success(self):
        """Тест успешного создания товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_conn.fetchrow.return_value = {
            'id': 1,
            'name': 'New Item',
            'price': Decimal('99.99'),
            'deleted': False
        }

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.post("/item", json={"name": "New Item", "price": 99.99})

            assert response.status_code == HTTPStatus.CREATED
            data = response.json()
            assert data['id'] == 1
            assert data['name'] == 'New Item'
            assert data['price'] == 99.99

    @pytest.mark.asyncio
    async def test_create_item_missing_fields(self):
        """Тест создания товара без обязательных полей"""
        response = client.post("/item", json={"name": "Only Name"})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

        response = client.post("/item", json={"price": 100.0})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_item_negative_price(self):
        """Тест создания товара с отрицательной ценой"""
        response = client.post("/item", json={"name": "Test", "price": -10.0})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_item_database_error(self):
        """Тест ошибки при создании товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = Exception("DB error")

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.post("/item", json={"name": "Test", "price": 100.0})

            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Error creating item" in response.json()['detail']

    @pytest.mark.asyncio
    async def test_update_item_success(self):
        """Тест успешного обновления товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {'id': 1, 'deleted': False},  # existing item check
            {'id': 1, 'name': 'Updated', 'price': Decimal('150.0'), 'deleted': False}  # updated item
        ]

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.put("/item/1", json={"name": "Updated", "price": 150.0})

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert data['name'] == 'Updated'
            assert data['price'] == 150.0

    @pytest.mark.asyncio
    async def test_update_item_not_found(self):
        """Тест обновления несуществующего товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.put("/item/999", json={"name": "Test", "price": 100.0})

            assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_item_deleted(self):
        """Тест обновления удаленного товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 1, 'deleted': True}

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.put("/item/1", json={"name": "Test", "price": 100.0})

            assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_item_missing_fields(self):
        """Тест обновления товара без обязательных полей"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 1, 'deleted': False}

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.put("/item/1", json={"name": "Only Name"})
            assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

            response = client.put("/item/1", json={"price": 100.0})
            assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_item_negative_price(self):
        """Тест обновления товара с отрицательной ценой"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 1, 'deleted': False}

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.put("/item/1", json={"name": "Test", "price": -10.0})
            assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_patch_item_success(self):
        """Тест успешного частичного обновления товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {'id': 1, 'name': 'Original', 'price': Decimal('100.0'), 'deleted': False},
            {'id': 1, 'name': 'Patched', 'price': Decimal('120.0'), 'deleted': False}
        ]

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.patch("/item/1", json={"name": "Patched", "price": 120.0})

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert data['name'] == 'Patched'
            assert data['price'] == 120.0


    @pytest.mark.asyncio
    async def test_patch_item_deleted(self):
        """Тест частичного обновления удаленного товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 1, 'name': 'Deleted', 'price': Decimal('100.0'), 'deleted': True}

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.patch("/item/1", json={"name": "Updated"})

            assert response.status_code == HTTPStatus.NOT_MODIFIED

    @pytest.mark.asyncio
    async def test_patch_item_extra_fields(self):
        """Тест частичного обновления с лишними полями"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 1, 'name': 'Original', 'price': Decimal('100.0'), 'deleted': False}

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.patch("/item/1", json={"name": "Test", "invalid_field": "value"})

            assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_patch_item_negative_price(self):
        """Тест частичного обновления с отрицательной ценой"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 1, 'name': 'Original', 'price': Decimal('100.0'), 'deleted': False}

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.patch("/item/1", json={"price": -10.0})

            assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_delete_item_success(self):
        """Тест успешного удаления товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 1, 'deleted': False}

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.delete("/item/1")

            assert response.status_code == HTTPStatus.OK

    @pytest.mark.asyncio
    async def test_delete_item_not_found(self):
        """Тест удаления несуществующего товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = None

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.delete("/item/999")

            assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_item_already_deleted(self):
        """Тест удаления уже удаленного товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 1, 'deleted': True}

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.delete("/item/1")

            assert response.status_code == HTTPStatus.OK  # Все равно успех

    @pytest.mark.asyncio
    async def test_delete_item_database_error(self):
        """Тест ошибки при удалении товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = Exception("DB error")

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.delete("/item/1")

            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Error deleting item" in response.json()['detail']


    @pytest.mark.asyncio
    async def test_get_cart_with_cache_empty_cart_data(self):
        """Тест получения корзины когда cart_data is None"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # Кеш пустой
        mock_redis.aclose = AsyncMock()

        with patch(f'{target}.get_redis_connection', return_value=mock_redis), \
                patch(f'{target}.get_cart_from_db', return_value=None):
            result = await main.get_cart_with_cache(1)

            assert result is None
            # Не должен вызывать setex если cart_data is None


    @pytest.mark.asyncio
    async def test_get_carts_with_quantity_filters_only_min(self):
        """Тест фильтрации корзин только по min_quantity"""
        mock_conn = AsyncMock()
        mock_carts = [
            {'id': 1, 'price': Decimal('100.0'), 'created_at': None, 'total_quantity': 3},
            {'id': 2, 'price': Decimal('50.0'), 'created_at': None, 'total_quantity': 1}
        ]
        mock_items = [
            [{'product_id': 1, 'quantity': 3, 'price': Decimal('33.33')}],
            [{'product_id': 2, 'quantity': 1, 'price': Decimal('50.0')}]
        ]

        mock_conn.fetch.side_effect = [mock_carts] + mock_items

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/cart?min_quantity=2")

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert len(data) == 1  # Только корзина с quantity >= 2
            assert data[0]['id'] == 1

    @pytest.mark.asyncio
    async def test_get_carts_with_quantity_filters_only_max(self):
        """Тест фильтрации корзин только по max_quantity"""
        mock_conn = AsyncMock()
        mock_carts = [
            {'id': 1, 'price': Decimal('100.0'), 'created_at': None, 'total_quantity': 3},
            {'id': 2, 'price': Decimal('50.0'), 'created_at': None, 'total_quantity': 1}
        ]
        mock_items = [
            [{'product_id': 1, 'quantity': 3, 'price': Decimal('33.33')}],
            [{'product_id': 2, 'quantity': 1, 'price': Decimal('50.0')}]
        ]

        mock_conn.fetch.side_effect = [mock_carts] + mock_items

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/cart?max_quantity=2")

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert len(data) == 1  # Только корзина с quantity <= 2
            assert data[0]['id'] == 2

    @pytest.mark.asyncio
    async def test_get_carts_with_quantity_filters_both(self):
        """Тест фильтрации корзин по min_quantity и max_quantity"""
        mock_conn = AsyncMock()
        mock_carts = [
            {'id': 1, 'price': Decimal('100.0'), 'created_at': None, 'total_quantity': 3},
            {'id': 2, 'price': Decimal('50.0'), 'created_at': None, 'total_quantity': 2},
            {'id': 3, 'price': Decimal('25.0'), 'created_at': None, 'total_quantity': 1}
        ]
        mock_items = [
            [{'product_id': 1, 'quantity': 3, 'price': Decimal('33.33')}],
            [{'product_id': 2, 'quantity': 2, 'price': Decimal('25.0')}],
            [{'product_id': 3, 'quantity': 1, 'price': Decimal('25.0')}]
        ]

        mock_conn.fetch.side_effect = [mock_carts] + mock_items

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/cart?min_quantity=2&max_quantity=2")

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert len(data) == 1  # Только корзина с quantity = 2
            assert data[0]['id'] == 2

    @pytest.mark.asyncio
    async def test_get_carts_with_quantity_filters_no_matches(self):
        """Тест фильтрации корзин когда нет совпадений"""
        mock_conn = AsyncMock()
        mock_carts = [
            {'id': 1, 'price': Decimal('100.0'), 'created_at': None, 'total_quantity': 5},
            {'id': 2, 'price': Decimal('50.0'), 'created_at': None, 'total_quantity': 10}
        ]
        mock_items = [
            [{'product_id': 1, 'quantity': 5, 'price': Decimal('20.0')}],
            [{'product_id': 2, 'quantity': 10, 'price': Decimal('5.0')}]
        ]

        mock_conn.fetch.side_effect = [mock_carts] + mock_items

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/cart?min_quantity=20")

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert len(data) == 0  # Нет корзин с quantity >= 20


    @pytest.mark.asyncio
    async def test_create_item_price_zero(self):
        """Тест создания товара с ценой 0"""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_conn.fetchrow.return_value = {
            'id': 1,
            'name': 'Free Item',
            'price': Decimal('0.0'),
            'deleted': False
        }

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.post("/item", json={"name": "Free Item", "price": 0.0})

            assert response.status_code == HTTPStatus.CREATED
            data = response.json()
            assert data['price'] == 0.0

    @pytest.mark.asyncio
    async def test_create_item_price_float_conversion(self):
        """Тест создания товара с преобразованием float цены"""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 1
        mock_conn.fetchrow.return_value = {
            'id': 1,
            'name': 'Test Item',
            'price': Decimal('99.99'),
            'deleted': False
        }

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.post("/item", json={"name": "Test Item", "price": 99.99})

            assert response.status_code == HTTPStatus.CREATED
            data = response.json()
            assert data['price'] == 99.99

    @pytest.mark.asyncio
    async def test_update_item_price_zero(self):
        """Тест обновления товара с ценой 0"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {'id': 1, 'deleted': False},  # existing item check
            {'id': 1, 'name': 'Free Item', 'price': Decimal('0.0'), 'deleted': False}  # updated item
        ]
        mock_conn.execute = AsyncMock()

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.put("/item/1", json={"name": "Free Item", "price": 0.0})

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert data['price'] == 0.0

    @pytest.mark.asyncio
    async def test_update_item_same_price(self):
        """Тест обновления товара с той же ценой"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {'id': 1, 'deleted': False},
            {'id': 1, 'name': 'Same Price', 'price': Decimal('100.0'), 'deleted': False}
        ]
        mock_conn.execute = AsyncMock()

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.put("/item/1", json={"name": "Same Price", "price": 100.0})

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert data['price'] == 100.0

    @pytest.mark.asyncio
    async def test_patch_item_only_name(self):
        """Тест частичного обновления только имени товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {'id': 1, 'name': 'Original', 'price': Decimal('100.0'), 'deleted': False},
            {'id': 1, 'name': 'Updated Name', 'price': Decimal('100.0'), 'deleted': False}
        ]
        mock_conn.execute = AsyncMock()

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.patch("/item/1", json={"name": "Updated Name"})

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert data['name'] == 'Updated Name'
            assert data['price'] == 100.0  # Цена не изменилась

    @pytest.mark.asyncio
    async def test_patch_item_only_price(self):
        """Тест частичного обновления только цены товара"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {'id': 1, 'name': 'Test Item', 'price': Decimal('50.0'), 'deleted': False},
            {'id': 1, 'name': 'Test Item', 'price': Decimal('75.0'), 'deleted': False}
        ]
        mock_conn.execute = AsyncMock()

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.patch("/item/1", json={"price": 75.0})

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert data['name'] == 'Test Item'  # Имя не изменилось
            assert data['price'] == 75.0

    @pytest.mark.asyncio
    async def test_patch_item_price_zero(self):
        """Тест частичного обновления цены на 0"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {'id': 1, 'name': 'Test Item', 'price': Decimal('100.0'), 'deleted': False},
            {'id': 1, 'name': 'Test Item', 'price': Decimal('0.0'), 'deleted': False}
        ]
        mock_conn.execute = AsyncMock()

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.patch("/item/1", json={"price": 0.0})

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert data['price'] == 0.0

    def test_decimal_encoder_other_types(self):
        """Тест DecimalEncoder с другими типами данных"""
        encoder = main.DecimalEncoder()

        # Тест с обычными типами
        test_data = {
            'string': 'test',
            'integer': 123,
            'float': 45.67,
            'list': [1, 2, 3],
            'none': None,
            'boolean': True
        }

        result = encoder.encode(test_data)
        parsed = json.loads(result)

        assert parsed['string'] == 'test'
        assert parsed['integer'] == 123
        assert parsed['float'] == 45.67
        assert parsed['list'] == [1, 2, 3]
        assert parsed['none'] is None
        assert parsed['boolean'] is True

    def test_decimal_encoder_nested_decimal(self):
        """Тест DecimalEncoder с вложенными Decimal"""
        encoder = main.DecimalEncoder()

        test_data = {
            'prices': [Decimal('10.50'), Decimal('20.75')],
            'nested': {
                'subprice': Decimal('30.25')
            }
        }

        result = encoder.encode(test_data)
        parsed = json.loads(result)

        assert parsed['prices'] == [10.50, 20.75]
        assert parsed['nested']['subprice'] == 30.25

    @pytest.mark.asyncio
    async def test_add_to_cart_success_existing_item(self):
        """Тест успешного добавления существующего товара в корзину"""
        with patch(f'{target}.get_db_connection') as mock_get_db, \
                patch(f'{target}.get_redis_connection'), \
                patch(f'{target}.get_cart_with_cache') as mock_get_cart, \
                patch(f'{target}.invalidate_cart_cache', new_callable=AsyncMock) as mock_invalidate:
            mock_conn = AsyncMock()
            mock_get_db.return_value = mock_conn

            # Базовые моки
            mock_conn.fetchval.return_value = True
            mock_conn.fetchrow.side_effect = [
                {'id': 1, 'name': 'Test', 'price': Decimal('50.0')},
                {'quantity': 1, 'price': Decimal('50.0')}
            ]
            mock_conn.execute = AsyncMock()

            # Transaction как простой async context manager
            mock_conn.transaction = MagicMock()
            mock_conn.transaction.return_value.__aenter__ = AsyncMock(return_value=None)
            mock_conn.transaction.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_get_cart.return_value = {
                'id': 1,
                'items': [{'id': 1, 'quantity': 2, 'price': 50.0}],
                'price': 100.0
            }

            response = client.post("/cart/1/add/1")

            assert response.status_code == HTTPStatus.OK
            mock_invalidate.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_patch_item_empty_body_fields(self):
        """Тест частичного обновления с пустыми полями в теле"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = {'id': 1, 'name': 'Original', 'price': Decimal('100.0'), 'deleted': False}

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.patch("/item/1", json={"name": "", "price": 0.0})

            assert response.status_code == HTTPStatus.OK
            # Должен обработать пустые значения без ошибки

    @pytest.mark.asyncio
    async def test_get_carts_empty_result(self):
        """Тест получения пустого списка корзин"""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []  # Нет корзин

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/cart")

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert data == []

    @pytest.mark.asyncio
    async def test_get_items_empty_result(self):
        """Тест получения пустого списка товаров"""
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []  # Нет товаров

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/item")

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert data == []

    @pytest.mark.asyncio
    async def test_get_items_show_deleted_false(self):
        """Тест получения товаров с show_deleted=false"""
        mock_conn = AsyncMock()
        mock_items = [
            {
                'id': 1,
                'name': 'Active Item',
                'price': Decimal('50.0'),
                'deleted': False,
                'created_at': None
            }
        ]
        mock_conn.fetch.return_value = mock_items

        with patch(f'{target}.get_db_connection', return_value=mock_conn):
            response = client.get("/item?show_deleted=false")

            assert response.status_code == HTTPStatus.OK
            data = response.json()
            assert len(data) == 1
            assert data[0]['deleted'] is False

    @pytest.mark.asyncio
    async def test_patch_item_not_found(self):
        """Тест частичного обновления несуществующего товара"""
        with patch(f'{target}.get_db_connection') as mock_get_db:
            mock_conn = AsyncMock()
            mock_get_db.return_value = mock_conn

            # Товар не существует
            mock_conn.fetchrow.return_value = None

            response = client.patch("/item/999", json={"name": "Updated Name"})

            assert response.status_code == HTTPStatus.NOT_FOUND
            assert "Item not found" in response.json()['detail']

    @pytest.mark.asyncio
    async def test_patch_item_empty_body(self):
        """Тест частичного обновления с пустым телом"""
        with patch(f'{target}.get_db_connection') as mock_get_db:
            mock_conn = AsyncMock()
            mock_get_db.return_value = mock_conn

            # Существующий товар
            existing_item = {
                'id': 1,
                'name': 'Original Name',
                'price': Decimal('100.0'),
                'deleted': False
            }
            mock_conn.fetchrow.return_value = existing_item

            # Не вызываем execute, так как обновления не должно быть

            response = client.patch("/item/1", json={})

            assert response.status_code == HTTPStatus.OK
            data = response.json()

            # Проверяем что вернулся товар без изменений
            assert data['id'] == 1
            assert data['name'] == 'Original Name'
            assert data['price'] == 100.0
            assert data['quantity'] == 1
            assert data['deleted'] is False

            # Проверяем что execute не вызывался (нет обновления в БД)
            mock_conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_to_cart_success_new_item(self):
        """Тест успешного добавления нового товара в корзину"""
        try:
            mock_conn = AsyncMock()

            # Включаем отладку для всех методов
            def debug_call(*args, **kwargs):
                print(f"Called: {args}, {kwargs}")
                return AsyncMock()

            mock_conn.fetchval = AsyncMock(return_value=True)
            mock_conn.fetchrow = AsyncMock(side_effect=[
                {'id': 1, 'name': 'New Product', 'price': Decimal('75.50')},
                None
            ])
            mock_conn.execute = AsyncMock()

            # Детальная настройка transaction
            mock_transaction = MagicMock()
            mock_transaction.__aenter__ = AsyncMock(return_value=None)
            mock_transaction.__aexit__ = AsyncMock(return_value=None)
            mock_conn.transaction = MagicMock(return_value=mock_transaction)

            with patch(f'{target}.get_db_connection', return_value=mock_conn), \
                    patch(f'{target}.get_redis_connection'), \
                    patch(f'{target}.get_cart_with_cache', return_value={'id': 1, 'items': [], 'price': 75.50}), \
                    patch(f'{target}.invalidate_cart_cache', new_callable=AsyncMock) as mock_invalidate:

                print("Before making request...")
                response = client.post("/cart/1/add/1")
                print(f"Response: {response.status_code}, {response.text}")

                assert response.status_code == HTTPStatus.OK

        except Exception as e:
            print(f"ERROR: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise
class TestDecimalEncoder:
    """Тесты для кастомного JSON энкодера"""

    def test_decimal_encoder(self):
        """Тест кодирования Decimal в JSON"""

        encoder = main.DecimalEncoder()

        # Тест с Decimal
        decimal_value = Decimal('123.45')
        result = encoder.encode({'price': decimal_value})
        assert '123.45' in result

        # Тест с обычными типами
        regular_data = {'name': 'test', 'number': 100}
        result = encoder.encode(regular_data)
        assert 'test' in result
        assert '100' in result
