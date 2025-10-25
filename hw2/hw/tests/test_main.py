"""
Полный набор тестов для Shop API

Включает тесты для:
- операций с товарами
- операций с корзинами
- валидации данных
- граничных случаев
- ошибок и исключений
- webSocket чата

"""

from http import HTTPStatus
from typing import Any
from uuid import uuid4
import pytest
from faker import Faker
from fastapi.testclient import TestClient

# НЕ ИМПОРТИРУЕМ models напрямую - они уже импортированы через conftest.py и main.py

faker = Faker()


@pytest.fixture()
def existing_empty_cart_id(client: TestClient) -> int:
    """Создаёт пустую корзину"""
    return client.post("/cart").json()["id"]


@pytest.fixture()
def existing_items(client: TestClient) -> list[dict[str, Any]]:
    """Создаёт 10 тестовых товаров"""
    items = []
    for i in range(10):
        item_data = {
            "name": f"Тестовый товар {i}",
            "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0),
        }
        response = client.post("/item", json=item_data)
        items.append(response.json())
    return items


@pytest.fixture()
def existing_not_empty_carts(client: TestClient, existing_items: list[dict[str, Any]]) -> list[int]:
    """Создаёт 20 заполненных корзин"""
    carts = []
    for i in range(20):
        cart_id: int = client.post("/cart").json()["id"]
        for item in faker.random_elements(existing_items, unique=False, length=min(i, len(existing_items))):
            client.post(f"/cart/{cart_id}/add/{item['id']}")
        carts.append(cart_id)
    return carts


@pytest.fixture()
def existing_not_empty_cart_id(
    client: TestClient,
    existing_empty_cart_id: int,
    existing_items: list[dict[str, Any]],
) -> int:
    """Создаёт корзину с 3 товарами"""
    for item in faker.random_elements(existing_items, unique=False, length=3):
        client.post(f"/cart/{existing_empty_cart_id}/add/{item['id']}")
    return existing_empty_cart_id


@pytest.fixture()
def existing_item(client: TestClient) -> dict[str, Any]:
    """Создаёт один тестовый товар"""
    return client.post(
        "/item",
        json={
            "name": f"Тестовый товар {uuid4().hex}",
            "price": faker.pyfloat(min_value=10.0, max_value=100.0),
        },
    ).json()


@pytest.fixture()
def deleted_item(client: TestClient, existing_item: dict[str, Any]) -> dict[str, Any]:
    """Создаёт удалённый товар"""
    item_id = existing_item["id"]
    client.delete(f"/item/{item_id}")
    existing_item["deleted"] = True
    return existing_item


def test_post_item(client: TestClient) -> None:
    """Тест создания товара"""
    item = {"name": "test item", "price": 9.99}
    response = client.post("/item", json=item)

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert item["price"] == data["price"]
    assert item["name"] == data["name"]
    assert "id" in data
    assert data["deleted"] is False


def test_post_item_invalid_price(client: TestClient) -> None:
    """Тест создания товара с некорректной ценой"""
    response = client.post("/item", json={"name": "test", "price": -10.0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    response = client.post("/item", json={"name": "test", "price": 0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_post_item_missing_fields(client: TestClient) -> None:
    """Тест создания товара без обязательных полей"""
    response = client.post("/item", json={"price": 10.0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    response = client.post("/item", json={"name": "test"})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    response = client.post("/item", json={})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_get_item(client: TestClient, existing_item: dict[str, Any]) -> None:
    """Тест получения товара по ID"""
    item_id = existing_item["id"]
    response = client.get(f"/item/{item_id}")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == existing_item


def test_get_item_not_found(client: TestClient) -> None:
    """Тест получения несуществующего товара"""
    response = client.get("/item/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_deleted_item(client: TestClient, deleted_item: dict[str, Any]) -> None:
    """Тест получения удалённого товара"""
    response = client.get(f"/item/{deleted_item['id']}")
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(
    ("query", "status_code"),
    [
        ({}, HTTPStatus.OK),
        ({"offset": 2, "limit": 5}, HTTPStatus.OK),
        ({"min_price": 5.0}, HTTPStatus.OK),
        ({"max_price": 5.0}, HTTPStatus.OK),
        ({"min_price": 10.0, "max_price": 50.0}, HTTPStatus.OK),
        ({"show_deleted": True}, HTTPStatus.OK),
        ({"show_deleted": False}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_get_item_list(client: TestClient, existing_items: list[dict[str, Any]], query: dict[str, Any], status_code: int) -> None:
    """Тест получения списка товаров с различными фильтрами"""
    response = client.get("/item", params=query)
    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        data = response.json()
        assert isinstance(data, list)
        
        for item in data:
            if "min_price" in query:
                assert item["price"] >= query["min_price"]
            
            if "max_price" in query:
                assert item["price"] <= query["max_price"]
            
            if "show_deleted" in query and not query["show_deleted"]:
                assert item["deleted"] is False


def test_get_item_list_pagination(client: TestClient, existing_items: list[dict[str, Any]]) -> None:
    """Тест пагинации списка товаров"""
    response = client.get("/item", params={"offset": 0, "limit": 5})
    page1 = response.json()
    assert len(page1) <= 5
    
    response = client.get("/item", params={"offset": 5, "limit": 5})
    page2 = response.json()
    
    page1_ids = {item["id"] for item in page1}
    page2_ids = {item["id"] for item in page2}
    assert page1_ids.isdisjoint(page2_ids)


def test_put_item(client: TestClient, existing_item: dict[str, Any]) -> None:
    """Тест полного обновления товара"""
    item_id = existing_item["id"]
    updated = {"name": "Updated name", "price": 99.99}
    response = client.put(f"/item/{item_id}", json=updated)
    
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["name"] == updated["name"]
    assert data["price"] == updated["price"]


def test_put_item_not_found(client: TestClient) -> None:
    """Тест обновления несуществующего товара"""
    response = client.put("/item/99999", json={"name": "test", "price": 10.0})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_patch_item(client: TestClient, existing_item: dict[str, Any]) -> None:
    """Тест частичного обновления товара"""
    item_id = existing_item["id"]
    
    # Обновляем только имя
    response = client.patch(f"/item/{item_id}", json={"name": "New name"})
    assert response.status_code == HTTPStatus.OK
    assert response.json()["name"] == "New name"
    assert response.json()["price"] == existing_item["price"]
    
    # Обновляем только цену
    response = client.patch(f"/item/{item_id}", json={"price": 55.55})
    assert response.status_code == HTTPStatus.OK
    assert response.json()["price"] == 55.55


def test_patch_item_not_found(client: TestClient) -> None:
    """Тест частичного обновления несуществующего товара"""
    response = client.patch("/item/99999", json={"name": "test"})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_patch_deleted_item(client: TestClient, deleted_item: dict[str, Any]) -> None:
    """Тест обновления удалённого товара"""
    response = client.patch(f"/item/{deleted_item['id']}", json={"name": "Updated"})
    assert response.status_code == HTTPStatus.NOT_MODIFIED


def test_patch_item_extra_fields(client: TestClient, existing_item: dict[str, Any]) -> None:
    """Тест PATCH с лишними полями"""
    response = client.patch(f"/item/{existing_item['id']}", json={
        "name": "Updated",
        "extra_field": "not allowed"
    })
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_delete_item(client: TestClient, existing_item: dict[str, Any]) -> None:
    """Тест удаления товара"""
    item_id = existing_item["id"]
    response = client.delete(f"/item/{item_id}")
    
    assert response.status_code == HTTPStatus.OK
    assert response.json()["deleted"] is True


def test_delete_item_not_found(client: TestClient) -> None:
    """Тест удаления несуществующего товара"""
    response = client.delete("/item/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_post_cart(client: TestClient) -> None:
    """Тест создания корзины"""
    response = client.post("/cart")
    
    assert response.status_code == HTTPStatus.CREATED
    assert "id" in response.json()
    assert "location" in response.headers
    assert response.headers["location"].startswith("/cart/")


def test_get_cart(client: TestClient, existing_empty_cart_id: int) -> None:
    """Тест получения пустой корзины"""
    response = client.get(f"/cart/{existing_empty_cart_id}")
    
    assert response.status_code == HTTPStatus.OK
    cart = response.json()
    assert cart["id"] == existing_empty_cart_id
    assert cart["items"] == []
    assert cart["price"] == 0.0


def test_get_cart_not_found(client: TestClient) -> None:
    """Тест получения несуществующей корзины"""
    response = client.get("/cart/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(
    ("query", "status_code"),
    [
        ({}, HTTPStatus.OK),
        ({"offset": 2, "limit": 5}, HTTPStatus.OK),
        ({"min_price": 5.0}, HTTPStatus.OK),
        ({"max_price": 100.0}, HTTPStatus.OK),
        ({"min_price": 10.0, "max_price": 100.0}, HTTPStatus.OK),
        ({"min_quantity": 1}, HTTPStatus.OK),
        ({"max_quantity": 10}, HTTPStatus.OK),
        ({"min_quantity": 1, "max_quantity": 5}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_quantity": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_quantity": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_get_cart_list(
    client: TestClient,
    existing_not_empty_carts: list[int],
    query: dict[str, Any],
    status_code: int
):
    """Тест получения списка корзин с фильтрами"""
    response = client.get("/cart", params=query)
    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        data = response.json()
        assert isinstance(data, list)

        for cart in data:
            if "min_price" in query:
                assert cart["price"] >= query["min_price"]

            if "max_price" in query:
                assert cart["price"] <= query["max_price"]

            total_quantity = sum(item["quantity"] for item in cart["items"])
            
            if "min_quantity" in query:
                assert total_quantity >= query["min_quantity"]

            if "max_quantity" in query:
                assert total_quantity <= query["max_quantity"]


def test_get_cart_list_pagination(client: TestClient, existing_not_empty_carts: list[int]) -> None:
    """Тест пагинации списка корзин"""
    response = client.get("/cart", params={"offset": 0, "limit": 5})
    page1 = response.json()
    assert len(page1) <= 5
    response = client.get("/cart", params={"offset": 5, "limit": 5})
    page2 = response.json()
    page1_ids = {cart["id"] for cart in page1}
    page2_ids = {cart["id"] for cart in page2}
    assert page1_ids.isdisjoint(page2_ids)


def test_add_item_to_cart(client: TestClient, existing_empty_cart_id: int, existing_item: dict[str, Any]) -> None:
    """Тест добавления товара в корзину"""
    cart_id = existing_empty_cart_id
    item_id = existing_item["id"]
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == HTTPStatus.OK
    
    cart = response.json()
    assert len(cart["items"]) == 1
    assert cart["items"][0]["id"] == item_id
    assert cart["items"][0]["quantity"] == 1
    assert cart["price"] == existing_item["price"]


def test_add_item_to_cart_multiple_times(client: TestClient, existing_empty_cart_id: int, existing_item: dict[str, Any]) -> None:
    """Тест добавления одного товара несколько раз"""
    cart_id = existing_empty_cart_id
    item_id = existing_item["id"]
    for i in range(1, 4):
        response = client.post(f"/cart/{cart_id}/add/{item_id}")
        cart = response.json()
        assert cart["items"][0]["quantity"] == i
        assert cart["price"] == pytest.approx(existing_item["price"] * i, 1e-8)


def test_add_multiple_items_to_cart(client: TestClient, existing_empty_cart_id: int, existing_items: list[dict[str, Any]]) -> None:
    """Тест добавления разных товаров в корзину"""
    cart_id = existing_empty_cart_id
    for item in existing_items[:3]:
        client.post(f"/cart/{cart_id}/add/{item['id']}")
    response = client.get(f"/cart/{cart_id}")
    cart = response.json()
    
    assert len(cart["items"]) == 3
    expected_price = sum(item["price"] for item in existing_items[:3])
    assert cart["price"] == pytest.approx(expected_price, 1e-8)


def test_add_item_to_cart_cart_not_found(client: TestClient, existing_item: dict[str, Any]) -> None:
    """Тест добавления товара в несуществующую корзину"""
    response = client.post(f"/cart/99999/add/{existing_item['id']}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_item_to_cart_item_not_found(client: TestClient, existing_empty_cart_id: int) -> None:
    """Тест добавления несуществующего товара в корзину"""
    response = client.post(f"/cart/{existing_empty_cart_id}/add/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_cart_with_deleted_item(client: TestClient, existing_empty_cart_id: int, existing_item: dict[str, Any]) -> None:
    """Тест поведения корзины с удалённым товаром"""
    cart_id = existing_empty_cart_id
    item_id = existing_item["id"]
    client.post(f"/cart/{cart_id}/add/{item_id}")
    client.delete(f"/item/{item_id}")
    response = client.get(f"/cart/{cart_id}")
    cart = response.json()
    
    assert len(cart["items"]) == 1
    assert cart["items"][0]["available"] is False
    assert cart["price"] == 0.0


def test_cart_with_mixed_items(client: TestClient, existing_empty_cart_id: int, existing_items: list[dict[str, Any]]) -> None:
    """Тест корзины со смешанными (доступными и удалёнными) товарами"""
    cart_id = existing_empty_cart_id
    for item in existing_items[:3]:
        client.post(f"/cart/{cart_id}/add/{item['id']}")
    client.delete(f"/item/{existing_items[1]['id']}")
    response = client.get(f"/cart/{cart_id}")
    cart = response.json()
    assert len(cart["items"]) == 3
    item_availabilities = {item["id"]: item["available"] for item in cart["items"]}
    assert item_availabilities[existing_items[0]["id"]] is True
    assert item_availabilities[existing_items[1]["id"]] is False
    assert item_availabilities[existing_items[2]["id"]] is True
    expected_price = existing_items[0]["price"] + existing_items[2]["price"]
    assert cart["price"] == pytest.approx(expected_price, 1e-8)


def test_websocket_chat_connection(client: TestClient) -> None:
    """Тест подключения к WebSocket чату"""
    with client.websocket_connect("/chat/test_room") as websocket:
        websocket.send_text("Hello")
        data = websocket.receive_text()
        assert " :: Hello" in data


def test_websocket_chat_multiple_clients(client: TestClient) -> None:
    """Тест обмена сообщениями между клиентами"""
    with client.websocket_connect("/chat/test_room") as ws1:
        with client.websocket_connect("/chat/test_room") as ws2:
            ws1.send_text("Message from client 1")
            msg1 = ws1.receive_text()
            msg2 = ws2.receive_text()
            
            assert "Message from client 1" in msg1
            assert "Message from client 1" in msg2


def test_websocket_different_rooms(client: TestClient) -> None:
    """Тест изоляции сообщений между комнатами"""
    with client.websocket_connect("/chat/room1") as ws1:
        with client.websocket_connect("/chat/room2") as ws2:
            ws1.send_text("Message to room1")
            msg1 = ws1.receive_text()
            
            assert "Message to room1" in msg1
            ws2.send_text("Message to room2")
            msg2 = ws2.receive_text()
            assert "Message to room2" in msg2
            assert "Message to room1" not in msg2


def test_metrics_endpoint(client: TestClient) -> None:
    """Тест эндпоинта метрик Prometheus"""
    response = client.get("/metrics")
    assert response.status_code == HTTPStatus.OK
    content = response.text
    assert "http_requests_total" in content or "process_" in content


def test_create_item_with_very_large_price(client: TestClient) -> None:
    """Тест создания товара с очень большой ценой"""
    response = client.post("/item", json={"name": "Expensive", "price": 999999999.99})
    assert response.status_code == HTTPStatus.CREATED


def test_create_item_with_very_small_price(client: TestClient) -> None:
    """Тест создания товара с минимальной ценой"""
    response = client.post("/item", json={"name": "Cheap", "price": 0.01})
    assert response.status_code == HTTPStatus.CREATED


def test_create_item_with_unicode_name(client: TestClient) -> None:
    """Тест создания товара с unicode символами в названии"""
    response = client.post("/item", json={"name": "Товар 测试", "price": 10.0})
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["name"] == "Товар 测试"


def test_get_items_empty_database(client: TestClient) -> None:
    """Тест получения товаров из пустой БД"""
    response = client.get("/item")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_get_carts_empty_database(client: TestClient) -> None:
    """Тест получения корзин из пустой БД"""
    response = client.get("/cart")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_price_calculation_precision(client: TestClient, existing_empty_cart_id: int) -> None:
    """Тест точности вычисления цены корзины"""
    cart_id = existing_empty_cart_id
    item1 = client.post("/item", json={"name": "Item1", "price": 0.1}).json()
    item2 = client.post("/item", json={"name": "Item2", "price": 0.2}).json()
    client.post(f"/cart/{cart_id}/add/{item1['id']}")
    client.post(f"/cart/{cart_id}/add/{item2['id']}")
    cart = client.get(f"/cart/{cart_id}").json()
    assert cart["price"] == pytest.approx(0.3, 1e-8)


# ==================== ТЕСТЫ ДЛЯ MODELS.PY ====================

def test_get_cart_item_quantity_direct(test_db, existing_empty_cart_id: int, existing_item: dict[str, Any]) -> None:
    """Тест прямого вызова get_cart_item_quantity"""
    from models import get_cart_item_quantity, set_cart_item_quantity
    
    cart_id = existing_empty_cart_id
    item_id = existing_item["id"]
    
    # Изначально количество должно быть 0
    quantity = get_cart_item_quantity(test_db, cart_id, item_id)
    assert quantity == 0
    
    # Добавляем товар
    set_cart_item_quantity(test_db, cart_id, item_id, 5)
    
    # Проверяем количество
    quantity = get_cart_item_quantity(test_db, cart_id, item_id)
    assert quantity == 5


def test_set_cart_item_quantity_update(test_db, existing_empty_cart_id: int, existing_item: dict[str, Any]) -> None:
    """Тест обновления количества товара (ветка update в set_cart_item_quantity)"""
    from models import set_cart_item_quantity, get_cart_item_quantity
    
    cart_id = existing_empty_cart_id
    item_id = existing_item["id"]
    
    # Добавляем товар первый раз (INSERT)
    set_cart_item_quantity(test_db, cart_id, item_id, 3)
    assert get_cart_item_quantity(test_db, cart_id, item_id) == 3
    
    # Обновляем количество (UPDATE) - это покроет ветку if existing
    set_cart_item_quantity(test_db, cart_id, item_id, 7)
    assert get_cart_item_quantity(test_db, cart_id, item_id) == 7


def test_get_cart_items_with_quantity_direct(test_db, existing_empty_cart_id: int, existing_items: list[dict[str, Any]]) -> None:
    """Тест прямого вызова get_cart_items_with_quantity"""
    from models import get_cart_items_with_quantity, set_cart_item_quantity
    
    cart_id = existing_empty_cart_id
    
    # Добавляем несколько товаров
    set_cart_item_quantity(test_db, cart_id, existing_items[0]["id"], 2)
    set_cart_item_quantity(test_db, cart_id, existing_items[1]["id"], 3)
    set_cart_item_quantity(test_db, cart_id, existing_items[2]["id"], 1)
    
    # Получаем товары с количеством
    items_with_qty = get_cart_items_with_quantity(test_db, cart_id)
    
    assert len(items_with_qty) == 3
    
    # Проверяем, что все товары есть
    item_quantities = {item.id: qty for item, qty in items_with_qty}
    assert item_quantities[existing_items[0]["id"]] == 2
    assert item_quantities[existing_items[1]["id"]] == 3
    assert item_quantities[existing_items[2]["id"]] == 1


def test_item_model_repr(test_db) -> None:
    """Тест метода __repr__ для ItemModel"""
    from models import ItemModel
    
    item = ItemModel(
        id=999,
        name="Test Item",
        price=99.99,
        deleted=False
    )
    
    repr_str = repr(item)
    assert "999" in repr_str
    assert "Test Item" in repr_str
    assert "99.99" in repr_str
    assert "False" in repr_str


def test_cart_model_repr(test_db) -> None:
    """Тест метода __repr__ для CartModel"""
    from models import CartModel
    
    cart = CartModel(id=888)
    
    repr_str = repr(cart)
    assert "888" in repr_str


def test_cart_with_nonexistent_item_in_db(test_db, existing_empty_cart_id: int) -> None:
    """Тест корзины с товаром, который был удален из БД"""
    from models import set_cart_item_quantity, get_cart_items_with_quantity, ItemModel
    
    cart_id = existing_empty_cart_id
    
    # Создаём товар
    item = ItemModel(name="Temp item", price=10.0, deleted=False)
    test_db.add(item)
    test_db.commit()
    test_db.refresh(item)
    item_id = item.id
    
    # Добавляем в корзину
    set_cart_item_quantity(test_db, cart_id, item_id, 3)
    
    # Удаляем товар из БД полностью (не soft delete)
    test_db.delete(item)
    test_db.commit()
    
    # Получаем товары корзины - должно вернуть пустой список
    items = get_cart_items_with_quantity(test_db, cart_id)
    assert len(items) == 0


# ==================== ТЕСТЫ ДЛЯ DATABASE.PY ====================

def test_get_db_dependency() -> None:
    """Тест генератора get_db"""
    from database import get_db
    
    # Получаем генератор
    db_generator = get_db()
    
    # Получаем сессию
    db_session = next(db_generator)
    assert db_session is not None
    
    # Проверяем, что сессия закрывается
    try:
        next(db_generator)
    except StopIteration:
        pass  # Это ожидаемо - генератор завершился


def test_init_db_function() -> None:
    """Тест функции init_db"""
    from database import init_db
    
    # Просто вызываем функцию - она должна работать без ошибок
    # В тестовом окружении это безопасно
    try:
        init_db()
    except Exception as e:
        # Если возникла ошибка из-за уже существующих таблиц - это нормально
        assert "already exists" in str(e).lower() or "table" in str(e).lower()


# ==================== ДОПОЛНИТЕЛЬНЫЕ EDGE CASES ====================

def test_multiple_carts_with_same_item(client: TestClient, existing_item: dict[str, Any]) -> None:
    """Тест добавления одного товара в разные корзины"""
    item_id = existing_item["id"]
    
    # Создаём 3 корзины
    cart1_id = client.post("/cart").json()["id"]
    cart2_id = client.post("/cart").json()["id"]
    cart3_id = client.post("/cart").json()["id"]
    
    # Добавляем один товар в разные корзины с разным количеством
    for _ in range(2):
        client.post(f"/cart/{cart1_id}/add/{item_id}")
    
    for _ in range(5):
        client.post(f"/cart/{cart2_id}/add/{item_id}")
    
    client.post(f"/cart/{cart3_id}/add/{item_id}")
    
    # Проверяем каждую корзину
    cart1 = client.get(f"/cart/{cart1_id}").json()
    cart2 = client.get(f"/cart/{cart2_id}").json()
    cart3 = client.get(f"/cart/{cart3_id}").json()
    
    assert cart1["items"][0]["quantity"] == 2
    assert cart2["items"][0]["quantity"] == 5
    assert cart3["items"][0]["quantity"] == 1


def test_get_cart_list_with_all_filters_combined(
    client: TestClient,
    existing_items: list[dict[str, Any]]
) -> None:
    """Тест списка корзин со всеми фильтрами одновременно"""
    # Создаём несколько корзин с разными характеристиками
    carts = []
    for i in range(5):
        cart_id = client.post("/cart").json()["id"]
        
        # Добавляем товары
        for j in range(i + 1):
            if j < len(existing_items):
                client.post(f"/cart/{cart_id}/add/{existing_items[j]['id']}")
        
        carts.append(cart_id)
    
    # Запрос со всеми фильтрами
    response = client.get("/cart", params={
        "offset": 1,
        "limit": 3,
        "min_price": 10.0,
        "max_price": 1000.0,
        "min_quantity": 1,
        "max_quantity": 10
    })
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 3


def test_item_price_boundaries(client: TestClient) -> None:
    """Тест граничных значений цены товара"""
    # Минимальная положительная цена
    response = client.post("/item", json={"name": "Min price", "price": 0.01})
    assert response.status_code == 201
    
    # Очень большая цена
    response = client.post("/item", json={"name": "Max price", "price": 999999999.99})
    assert response.status_code == 201
    
    # Цена с множеством десятичных знаков
    response = client.post("/item", json={"name": "Precise", "price": 12.3456789})
    assert response.status_code == 201


def test_patch_item_with_only_price(client: TestClient, existing_item: dict[str, Any]) -> None:
    """Тест PATCH с обновлением только цены"""
    item_id = existing_item["id"]
    
    response = client.patch(f"/item/{item_id}", json={"price": 199.99})
    assert response.status_code == 200
    
    data = response.json()
    assert data["price"] == 199.99
    assert data["name"] == existing_item["name"]  # Имя не изменилось


def test_patch_item_with_only_name(client: TestClient, existing_item: dict[str, Any]) -> None:
    """Тест PATCH с обновлением только имени"""
    item_id = existing_item["id"]
    
    response = client.patch(f"/item/{item_id}", json={"name": "New Name Only"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "New Name Only"
    assert data["price"] == existing_item["price"]  # Цена не изменилась


def test_empty_cart_price(client: TestClient, existing_empty_cart_id: int) -> None:
    """Тест что пустая корзина имеет цену 0"""
    response = client.get(f"/cart/{existing_empty_cart_id}")
    cart = response.json()
    
    assert cart["price"] == 0.0
    assert cart["items"] == []


def test_get_items_show_deleted_false(client: TestClient, existing_item: dict[str, Any]) -> None:
    """Тест что удалённые товары не показываются по умолчанию"""
    # Удаляем товар
    client.delete(f"/item/{existing_item['id']}")
    
    # Запрашиваем список без show_deleted
    response = client.get("/item")
    items = response.json()
    
    # Удалённого товара не должно быть в списке
    item_ids = [item["id"] for item in items]
    assert existing_item["id"] not in item_ids


def test_get_items_show_deleted_true(client: TestClient, existing_item: dict[str, Any]) -> None:
    """Тест что удалённые товары показываются с show_deleted=true"""
    # Удаляем товар
    client.delete(f"/item/{existing_item['id']}")
    
    # Запрашиваем список с show_deleted=true
    response = client.get("/item", params={"show_deleted": True})
    items = response.json()
    
    # Удалённый товар должен быть в списке
    deleted_items = [item for item in items if item["id"] == existing_item["id"]]
    assert len(deleted_items) == 1
    assert deleted_items[0]["deleted"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=shop_api", "--cov-report=html", "--cov-report=term"])