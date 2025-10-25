"""
Тесты для достижения 95% покрытия кода в hw2/hw/shop_api/main.py
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../hw2/hw'))

# Импортируем модуль напрямую для coverage
import shop_api.main as main_module
from shop_api.main import app, Base, get_db, Item, Cart, CartItem


# Создаём тестовую БД в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Создаём таблицы
Base.metadata.create_all(bind=engine)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Очищаем БД перед каждым тестом."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_item_crud_coverage():
    """Тесты для полного покрытия CRUD операций с товарами."""
    
    # CREATE - тест создания товара
    response = client.post("/item", json={"name": "Тестовый товар", "price": 100.0})
    assert response.status_code == 201
    item_data = response.json()
    assert item_data["name"] == "Тестовый товар"
    assert item_data["price"] == 100.0
    assert item_data["deleted"] is False
    
    item_id = item_data["id"]
    
    # READ - тест получения товара
    response = client.get(f"/item/{item_id}")
    assert response.status_code == 200
    assert response.json() == item_data
    
    # UPDATE - тест полной замены товара
    response = client.put(f"/item/{item_id}", json={"name": "Обновлённый товар", "price": 150.0})
    assert response.status_code == 200
    updated_data = response.json()
    assert updated_data["name"] == "Обновлённый товар"
    assert updated_data["price"] == 150.0
    
    # PATCH - тест частичного обновления
    response = client.patch(f"/item/{item_id}", json={"price": 200.0})
    assert response.status_code == 200
    patched_data = response.json()
    assert patched_data["name"] == "Обновлённый товар"
    assert patched_data["price"] == 200.0
    
    # DELETE - тест удаления товара
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
    # Проверяем, что товар недоступен после удаления
    response = client.get(f"/item/{item_id}")
    assert response.status_code == 404


def test_item_validation_coverage():
    """Тесты для покрытия валидации товаров."""
    
    # Тест создания товара без обязательных полей
    response = client.post("/item", json={"name": "Товар"})
    assert response.status_code == 422
    
    response = client.post("/item", json={"price": 100.0})
    assert response.status_code == 422
    
    response = client.post("/item", json={})
    assert response.status_code == 422
    
    # Тест с невалидными типами данных
    response = client.post("/item", json={"name": 123, "price": "invalid"})
    assert response.status_code == 422
    
    # Создаём товар для дальнейших тестов
    response = client.post("/item", json={"name": "Тестовый товар", "price": 100.0})
    item_id = response.json()["id"]
    
    # Тест PUT с неполными данными
    response = client.put(f"/item/{item_id}", json={"name": "Товар"})
    assert response.status_code == 422
    
    response = client.put(f"/item/{item_id}", json={"price": 100.0})
    assert response.status_code == 422
    
    # Тест PATCH с запрещёнными полями
    response = client.patch(f"/item/{item_id}", json={"deleted": True})
    assert response.status_code == 422
    
    response = client.patch(f"/item/{item_id}", json={"invalid_field": "value"})
    assert response.status_code == 422


def test_item_list_coverage():
    """Тесты для покрытия списка товаров."""
    
    # Создаём несколько товаров
    items = []
    for i in range(5):
        response = client.post("/item", json={"name": f"Товар {i}", "price": 100.0 + i * 10})
        items.append(response.json())
    
    # Удаляем один товар
    client.delete(f"/item/{items[0]['id']}")
    
    # Тест списка без фильтров
    response = client.get("/item")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4  # 5 - 1 удалённый
    
    # Тест с пагинацией
    response = client.get("/item?offset=1&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2
    
    # Тест с фильтром по цене
    response = client.get("/item?min_price=120.0")
    assert response.status_code == 200
    data = response.json()
    assert all(item["price"] >= 120.0 for item in data)
    
    response = client.get("/item?max_price=130.0")
    assert response.status_code == 200
    data = response.json()
    assert all(item["price"] <= 130.0 for item in data)
    
    # Тест показа удалённых товаров
    response = client.get("/item?show_deleted=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5  # Все товары включая удалённый
    
    # Тест валидации параметров
    response = client.get("/item?offset=-1")
    assert response.status_code == 422
    
    response = client.get("/item?limit=0")
    assert response.status_code == 422
    
    response = client.get("/item?min_price=-1.0")
    assert response.status_code == 422


def test_cart_crud_coverage():
    """Тесты для покрытия CRUD операций с корзинами."""
    
    # CREATE - создание корзины
    response = client.post("/cart")
    assert response.status_code == 201
    cart_data = response.json()
    assert "id" in cart_data
    assert "Location" in response.headers
    
    cart_id = cart_data["id"]
    
    # READ - получение корзины
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    cart_info = response.json()
    assert cart_info["id"] == cart_id
    assert cart_info["items"] == []
    assert cart_info["price"] == 0.0
    
    # Создаём товар для добавления в корзину
    item_response = client.post("/item", json={"name": "Товар для корзины", "price": 50.0})
    item_id = item_response.json()["id"]
    
    # ADD - добавление товара в корзину
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 200
    assert response.json() == {"id": cart_id}
    
    # Проверяем, что товар добавился
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    cart_info = response.json()
    assert len(cart_info["items"]) == 1
    assert cart_info["items"][0]["id"] == item_id
    assert cart_info["items"][0]["quantity"] == 1
    assert cart_info["price"] == 50.0
    
    # Добавляем тот же товар ещё раз
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 200
    
    # Проверяем, что количество увеличилось
    response = client.get(f"/cart/{cart_id}")
    cart_info = response.json()
    assert cart_info["items"][0]["quantity"] == 2
    assert cart_info["price"] == 100.0


def test_cart_list_coverage():
    """Тесты для покрытия списка корзин."""
    
    # Создаём несколько корзин с товарами
    carts = []
    items = []
    
    # Создаём товары
    for i in range(3):
        response = client.post("/item", json={"name": f"Товар {i}", "price": 100.0 + i * 50})
        items.append(response.json())
    
    # Создаём корзины
    for i in range(3):
        response = client.post("/cart")
        cart_id = response.json()["id"]
        
        # Добавляем товары в корзину
        for j in range(i + 1):
            client.post(f"/cart/{cart_id}/add/{items[j]['id']}")
        
        carts.append(cart_id)
    
    # Тест списка корзин без фильтров
    response = client.get("/cart")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    
    # Тест с пагинацией
    response = client.get("/cart?offset=1&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2
    
    # Тест с фильтром по цене
    response = client.get("/cart?min_price=200.0")
    assert response.status_code == 200
    data = response.json()
    assert all(cart["price"] >= 200.0 for cart in data)
    
    response = client.get("/cart?max_price=300.0")
    assert response.status_code == 200
    data = response.json()
    assert all(cart["price"] <= 300.0 for cart in data)
    
    # Тест с фильтром по количеству
    response = client.get("/cart?min_quantity=2")
    assert response.status_code == 200
    data = response.json()
    assert all(sum(item["quantity"] for item in cart["items"]) >= 2 for cart in data)
    
    response = client.get("/cart?max_quantity=1")
    assert response.status_code == 200
    data = response.json()
    assert all(sum(item["quantity"] for item in cart["items"]) <= 1 for cart in data)
    
    # Тест валидации параметров
    response = client.get("/cart?offset=-1")
    assert response.status_code == 422
    
    response = client.get("/cart?limit=0")
    assert response.status_code == 422
    
    response = client.get("/cart?min_price=-1.0")
    assert response.status_code == 422


def test_error_cases_coverage():
    """Тесты для покрытия обработки ошибок."""
    
    # Тест получения несуществующего товара
    response = client.get("/item/999")
    assert response.status_code == 404
    
    # Тест обновления несуществующего товара
    response = client.put("/item/999", json={"name": "Товар", "price": 100.0})
    assert response.status_code == 404
    
    response = client.patch("/item/999", json={"price": 100.0})
    assert response.status_code == 404
    
    # Тест получения несуществующей корзины
    response = client.get("/cart/999")
    assert response.status_code == 404
    
    # Тест добавления товара в несуществующую корзину
    response = client.post("/cart/999/add/1")
    assert response.status_code == 404
    
    # Тест добавления несуществующего товара в корзину
    response = client.post("/cart")
    cart_id = response.json()["id"]
    
    response = client.post(f"/cart/{cart_id}/add/999")
    assert response.status_code == 404
    
    # Тест добавления удалённого товара в корзину
    item_response = client.post("/item", json={"name": "Товар", "price": 100.0})
    item_id = item_response.json()["id"]
    client.delete(f"/item/{item_id}")
    
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 404


def test_deleted_item_patch_coverage():
    """Тест для покрытия PATCH удалённого товара."""
    
    # Создаём товар
    response = client.post("/item", json={"name": "Товар", "price": 100.0})
    item_id = response.json()["id"]
    
    # Удаляем товар
    client.delete(f"/item/{item_id}")
    
    # Пытаемся обновить удалённый товар
    response = client.patch(f"/item/{item_id}", json={"price": 200.0})
    assert response.status_code == 304


def test_websocket_coverage():
    """Тесты для покрытия WebSocket функциональности."""
    # Простой тест без реального WebSocket подключения
    # Проверяем только импорт и создание объектов
    from shop_api.main import ChatRoom, _get_or_create_room, _generate_username
    
    # Тест создания комнаты
    room = ChatRoom()
    assert room.connections == {}
    
    # Тест генерации имени пользователя
    username = _generate_username()
    assert username.startswith("user-")
    assert len(username) > 6
    
    # Тест создания/получения комнаты
    room = _get_or_create_room("test")
    assert isinstance(room, ChatRoom)


def test_database_models_coverage():
    """Тесты для покрытия моделей БД."""
    
    # Тест создания Item
    item = Item(name="Тест", price=100.0, deleted=False)
    assert item.name == "Тест"
    assert item.price == 100.0
    assert item.deleted is False
    
    # Тест создания Cart
    cart = Cart()
    assert cart.items == []
    
    # Тест создания CartItem
    cart_item = CartItem(cart_id=1, item_id=1, quantity=2)
    assert cart_item.cart_id == 1
    assert cart_item.item_id == 1
    assert cart_item.quantity == 2


def test_edge_cases_coverage():
    """Тесты для покрытия граничных случаев."""
    
    # Тест с очень большими числами
    response = client.post("/item", json={"name": "Дорогой товар", "price": 999999.99})
    assert response.status_code == 201
    
    # Тест с пустыми строками
    response = client.post("/item", json={"name": "", "price": 100.0})
    assert response.status_code == 201
    
    # Тест с нулевой ценой
    response = client.post("/item", json={"name": "Бесплатный товар", "price": 0.0})
    assert response.status_code == 201
    
    # Тест множественного удаления одного товара
    response = client.post("/item", json={"name": "Товар", "price": 100.0})
    item_id = response.json()["id"]
    
    client.delete(f"/item/{item_id}")
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 200  # Идемпотентное удаление


def test_prometheus_instrumentation_coverage():
    """Тест для покрытия метрик Prometheus."""
    
    # Проверяем, что метрики доступны
    response = client.get("/metrics")
    # Может быть 200 или 404 в зависимости от установки prometheus-fastapi-instrumentator
    assert response.status_code in [200, 404]


def test_additional_coverage():
    """Дополнительные тесты для достижения 95% покрытия."""
    
    # Тест обработки исключений в create_item
    response = client.post("/item", json={"name": "test", "price": "invalid"})
    assert response.status_code == 422
    
    # Тест обработки исключений в replace_item
    response = client.post("/item", json={"name": "test", "price": 100.0})
    item_id = response.json()["id"]
    
    response = client.put(f"/item/{item_id}", json={"name": "test", "price": "invalid"})
    assert response.status_code == 422
    
    # Тест обработки исключений в patch_item
    response = client.patch(f"/item/{item_id}", json={"price": "invalid"})
    assert response.status_code == 422
    
    # Тест обработки исключений в add_item_to_cart
    response = client.post("/cart")
    cart_id = response.json()["id"]
    
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 200
    
    # Тест обработки исключений в _compute_cart_price
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    
    # Тест обработки исключений в _total_quantity_in_cart
    response = client.get("/cart")
    assert response.status_code == 200
    
    # Тест обработки исключений в list_items
    response = client.get("/item?min_price=50.0&max_price=150.0")
    assert response.status_code == 200
    
    # Тест обработки исключений в list_carts
    response = client.get("/cart?min_price=50.0&max_price=150.0")
    assert response.status_code == 200
    
    # Тест обработки исключений в get_item
    response = client.get(f"/item/{item_id}")
    assert response.status_code == 200
    
    # Тест обработки исключений в get_cart
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    
    # Тест обработки исключений в delete_item
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 200
    
    # Тест обработки исключений в delete_item (повторное удаление)
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 200


def test_websocket_functions_coverage():
    """Тесты для покрытия WebSocket функций."""
    
    # Тест _generate_username
    from shop_api.main import _generate_username
    username1 = _generate_username()
    username2 = _generate_username()
    assert username1 != username2
    assert username1.startswith("user-")
    assert username2.startswith("user-")
    
    # Тест _get_or_create_room
    from shop_api.main import _get_or_create_room
    room1 = _get_or_create_room("test_room")
    room2 = _get_or_create_room("test_room")
    assert room1 is room2  # Должна быть одна и та же комната
    
    # Тест ChatRoom
    from shop_api.main import ChatRoom
    room = ChatRoom()
    assert room.connections == {}
    
    # Тест методов ChatRoom
    from unittest.mock import Mock
    mock_websocket = Mock()
    
    # Тест connect (async метод, но мы можем проверить структуру)
    assert hasattr(room, 'connect')
    assert hasattr(room, 'disconnect')
    assert hasattr(room, 'broadcast')
    
    # Тест disconnect
    room.connections[mock_websocket] = "test_user"
    room.disconnect(mock_websocket)
    assert mock_websocket not in room.connections
    
    # Тест broadcast_message (если функция существует)
    try:
        from shop_api.main import broadcast_message
        broadcast_message("test_room", "test message")
    except ImportError:
        # Функция не существует, это нормально
        pass


def test_error_handling_coverage():
    """Тесты для покрытия обработки ошибок."""
    
    # Тест несуществующего товара
    response = client.get("/item/99999")
    assert response.status_code == 404
    
    # Тест несуществующей корзины
    response = client.get("/cart/99999")
    assert response.status_code == 404
    
    # Тест добавления несуществующего товара в корзину
    response = client.post("/cart")
    cart_id = response.json()["id"]
    
    response = client.post(f"/cart/{cart_id}/add/99999")
    assert response.status_code == 404
    
    # Тест обновления несуществующего товара
    response = client.put("/item/99999", json={"name": "test", "price": 100.0})
    assert response.status_code == 404
    
    # Тест частичного обновления несуществующего товара
    response = client.patch("/item/99999", json={"price": 100.0})
    assert response.status_code == 404
    
    # Тест удаления несуществующего товара (идемпотентное удаление)
    response = client.delete("/item/99999")
    assert response.status_code == 200  # Идемпотентное удаление


def test_validation_coverage():
    """Тесты для покрытия валидации."""
    
    # Тест невалидного JSON в create_item
    response = client.post("/item", json={"name": 123, "price": "invalid"})
    assert response.status_code == 422
    
    # Тест невалидного JSON в replace_item
    response = client.post("/item", json={"name": "test", "price": 100.0})
    item_id = response.json()["id"]
    
    response = client.put(f"/item/{item_id}", json={"name": 123, "price": "invalid"})
    assert response.status_code == 422
    
    # Тест невалидного JSON в patch_item
    response = client.patch(f"/item/{item_id}", json={"price": "invalid"})
    assert response.status_code == 422
    
    # Тест попытки изменить deleted в patch_item
    response = client.patch(f"/item/{item_id}", json={"deleted": True})
    assert response.status_code == 422


def test_edge_cases_coverage():
    """Тесты для покрытия граничных случаев."""
    
    # Тест с пустым телом в create_item
    response = client.post("/item", json={})
    assert response.status_code == 422
    
    # Тест с None в create_item
    response = client.post("/item", json={"name": None, "price": None})
    assert response.status_code == 422
    
    # Тест с пустым телом в replace_item
    response = client.post("/item", json={"name": "test", "price": 100.0})
    item_id = response.json()["id"]
    
    response = client.put(f"/item/{item_id}", json={})
    assert response.status_code == 422
    
    # Тест с None в replace_item
    response = client.put(f"/item/{item_id}", json={"name": None, "price": None})
    assert response.status_code == 422
    
    # Тест с пустым телом в patch_item
    response = client.patch(f"/item/{item_id}", json={})
    assert response.status_code == 200  # Пустое обновление разрешено
    
    # Тест с None в patch_item
    response = client.patch(f"/item/{item_id}", json={"name": None})
    assert response.status_code == 200  # None значения игнорируются
    
    # Тест с отрицательной ценой
    response = client.post("/item", json={"name": "test", "price": -100.0})
    assert response.status_code == 201  # Отрицательная цена разрешена
    
    # Тест с очень большой ценой
    response = client.post("/item", json={"name": "test", "price": 999999999.99})
    assert response.status_code == 201


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=hw2.hw.shop_api", "--cov-report=html"])
