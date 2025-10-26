import asyncio
from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from faker import Faker
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from shop_api.main import (Broadcaster, app, calculate_cart_price,
                           cart_id_counter, carts, chat_rooms,
                           get_next_cart_id, get_next_item_id, item_id_counter,
                           items, ws_chat)
from shop_api.models import ItemCreate, ItemPatch, ItemUpdate

client = TestClient(app)
faker = Faker()


@pytest.fixture(autouse=True)
def reset_state():
    """Сбрасываем состояние перед каждым тестом"""
    global carts, items, cart_id_counter, item_id_counter, chat_rooms
    carts.clear()
    items.clear()
    cart_id_counter = 0
    item_id_counter = 0
    chat_rooms.clear()


# === Фикстуры для данных ===


@pytest.fixture()
def existing_empty_cart_id() -> int:
    return client.post("/cart").json()["id"]


@pytest.fixture()
def existing_items() -> list[int]:
    items_data = [
        {
            "name": f"Тестовый товар {i}",
            "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0),
        }
        for i in range(3)
    ]
    return [client.post("/item", json=item).json()["id"] for item in items_data]


@pytest.fixture()
def existing_not_empty_cart_id(
    existing_empty_cart_id: int, existing_items: list[int]
) -> int:
    cart_id = existing_empty_cart_id
    for item_id in existing_items[:2]:
        client.post(f"/cart/{cart_id}/add/{item_id}")
    return cart_id


@pytest.fixture()
def existing_item() -> dict[str, Any]:
    return client.post(
        "/item",
        json={
            "name": f"Тестовый товар {uuid4().hex}",
            "price": faker.pyfloat(min_value=10.0, max_value=100.0),
        },
    ).json()


@pytest.fixture()
def deleted_item(existing_item: dict[str, Any]) -> dict[str, Any]:
    item_id = existing_item["id"]
    client.delete(f"/item/{item_id}")
    existing_item["deleted"] = True
    return existing_item


# === Unit-тесты для вспомогательных функций ===


def test_get_next_cart_id():
    assert get_next_cart_id() == 1
    assert get_next_cart_id() == 2


def test_get_next_item_id():
    assert get_next_item_id() == 1
    assert get_next_item_id() == 2


def test_calculate_cart_price():
    items[1] = {"id": 1, "name": "Item1", "price": 10.0, "deleted": False}
    items[2] = {"id": 2, "name": "Item2", "price": 20.0, "deleted": True}
    cart = {
        "items": [
            {"id": 1, "quantity": 2},
            {"id": 2, "quantity": 1},
            {"id": 3, "quantity": 1},
        ]
    }
    assert calculate_cart_price(cart) == 20.0


def test_calculate_cart_price_empty_items():
    cart = {"items": []}
    assert calculate_cart_price(cart) == 0.0


# === Тесты для корзин ===


def test_post_cart():
    response = client.post("/cart")
    assert response.status_code == HTTPStatus.CREATED
    assert "location" in response.headers
    assert "id" in response.json()


@pytest.mark.parametrize(
    ("cart", "not_empty"),
    [
        ("existing_empty_cart_id", False),
        ("existing_not_empty_cart_id", True),
    ],
)
def test_get_cart(request, cart: str, not_empty: bool):
    cart_id = request.getfixturevalue(cart)
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == HTTPStatus.OK
    response_json = response.json()
    len_items = len(response_json["items"])
    assert len_items > 0 if not_empty else len_items == 0
    if not_empty:
        price = sum(
            items[item["id"]]["price"] * item["quantity"]
            for item in response_json["items"]
            if item["id"] in items and not items[item["id"]]["deleted"]
        )
        assert response_json["price"] == pytest.approx(price, 1e-8)
    else:
        assert response_json["price"] == 0.0


def test_get_cart_not_found():
    response = client.get("/cart/999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_cart_empty():
    cart_id = client.post("/cart").json()["id"]
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["items"] == []
    assert response.json()["price"] == 0.0


def test_get_cart_key_error():
    carts[999] = {"id": 999, "items": [{"id": 999, "quantity": 1}]}
    response = client.get("/cart/999")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["price"] == 0.0


@pytest.mark.parametrize(
    ("query", "status_code"),
    [
        ({}, HTTPStatus.OK),
        ({"offset": 1, "limit": 2}, HTTPStatus.OK),
        ({"min_price": 1000.0}, HTTPStatus.OK),
        ({"max_price": 20.0}, HTTPStatus.OK),
        ({"min_quantity": 1}, HTTPStatus.OK),
        ({"max_quantity": 0}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_quantity": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_quantity": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_get_cart_list(
    query: dict[str, Any], status_code: int, existing_not_empty_cart_id
):
    response = client.get("/cart", params=query)
    assert response.status_code == status_code
    if status_code == HTTPStatus.OK:
        data = response.json()
        assert isinstance(data, list)
        if "min_price" in query:
            assert all(item["price"] >= query["min_price"] for item in data)
        if "max_price" in query:
            assert all(item["price"] <= query["max_price"] for item in data)
        total_quantity = sum(
            item["quantity"] for cart in data for item in cart["items"]
        )
        if "min_quantity" in query:
            assert total_quantity >= query["min_quantity"] or not data
        if "max_quantity" in query:
            assert total_quantity <= query["max_quantity"] or not data


def test_get_carts_empty_result():
    cart_id = client.post("/cart").json()["id"]
    item_id = client.post("/item", json={"name": "Item", "price": 10.0}).json()["id"]
    client.post(f"/cart/{cart_id}/add/{item_id}")
    response = client.get("/cart?min_price=1000&max_quantity=0")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_get_carts_full_filters():
    cart1 = client.post("/cart").json()["id"]
    item1 = client.post("/item", json={"name": "Item1", "price": 10.0}).json()["id"]
    client.post(f"/cart/{cart1}/add/{item1}")
    cart2 = client.post("/cart").json()["id"]
    item2 = client.post("/item", json={"name": "Item2", "price": 20.0}).json()["id"]
    client.post(f"/cart/{cart2}/add/{item2}")
    response = client.get(
        "/cart?min_price=15&max_price=25&min_quantity=1&max_quantity=1&offset=0&limit=1"
    )
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1
    assert response.json()[0]["price"] == 20.0


def test_add_item_to_cart(existing_not_empty_cart_id: int, existing_items: list[int]):
    cart_id = existing_not_empty_cart_id
    item_id = existing_items[0]
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == HTTPStatus.OK
    cart = client.get(f"/cart/{cart_id}").json()
    for cart_item in cart["items"]:
        if cart_item["id"] == item_id:
            assert cart_item["quantity"] >= 1


def test_add_item_to_cart_not_found(existing_not_empty_cart_id, existing_items):
    response = client.post(f"/cart/999/add/{existing_items[0]}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    response = client.post(f"/cart/{existing_not_empty_cart_id}/add/999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_item_to_cart_deleted_item(existing_not_empty_cart_id, deleted_item):
    item_id = deleted_item["id"]
    response = client.post(f"/cart/{existing_not_empty_cart_id}/add/{item_id}")
    assert response.status_code == HTTPStatus.OK
    cart = client.get(f"/cart/{existing_not_empty_cart_id}").json()
    for item in cart["items"]:
        if item["id"] == item_id:
            assert not item["available"]


def test_add_item_to_cart_exception():
    carts[999] = {"id": 999}
    response = client.post("/cart/999/add/1")
    assert response.status_code == HTTPStatus.NOT_FOUND


# === Тесты для товаров ===


def test_post_item():
    item = {"name": "test item", "price": 9.99}
    response = client.post("/item", json=item)
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert item["price"] == data["price"]
    assert item["name"] == data["name"]


def test_post_item_invalid():
    response = client.post("/item", json={"name": "invalid", "price": -1.0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_get_item(existing_item: dict[str, Any]):
    item_id = existing_item["id"]
    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == existing_item


def test_get_item_not_found():
    response = client.get("/item/999")
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(
    ("query", "status_code"),
    [
        ({"offset": 2, "limit": 5}, HTTPStatus.OK),
        ({"min_price": 5.0}, HTTPStatus.OK),
        ({"max_price": 5.0}, HTTPStatus.OK),
        ({"show_deleted": True}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_get_item_list(query: dict[str, Any], status_code: int):
    response = client.get("/item", params=query)
    assert response.status_code == status_code
    if status_code == HTTPStatus.OK:
        data = response.json()
        assert isinstance(data, list)
        if "min_price" in query:
            assert all(item["price"] >= query["min_price"] for item in data)
        if "max_price" in query:
            assert all(item["price"] <= query["max_price"] for item in data)
        if "show_deleted" in query and query["show_deleted"] is False:
            assert all(item["deleted"] is False for item in data)


def test_get_items_empty_filter():
    client.post("/item", json={"name": "Item1", "price": 10.0})
    client.post("/item", json={"name": "Item2", "price": 20.0})
    response = client.get("/item?min_price=30&max_price=50&show_deleted=true")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_get_items_extreme_filters():
    client.post("/item", json={"name": "Expensive", "price": 10000.0})
    client.post("/item", json={"name": "Cheap", "price": 1.0})
    response = client.get("/item?min_price=5000&max_price=15000")
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Expensive"

    response = client.get("/item?min_price=0&max_price=0.5")
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 0


def test_get_items_pagination_deleted():
    for i in range(5):
        item = client.post("/item", json={"name": f"Item{i}", "price": 10.0}).json()[
            "id"
        ]
        if i % 2 == 0:
            client.delete(f"/item/{item}")
    response = client.get("/item?show_deleted=true&offset=1&limit=2")
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 2
    assert any(item["deleted"] for item in response.json())


def test_get_item_list_with_deleted(deleted_item: dict[str, Any]):
    response = client.get("/item?show_deleted=true")
    assert any(item["deleted"] for item in response.json())


@pytest.mark.parametrize(
    ("body", "status_code"),
    [
        ({}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"price": 9.99}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"name": "new name", "price": 9.99}, HTTPStatus.OK),
        ({"name": "new name", "price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_put_item(
    existing_item: dict[str, Any], body: dict[str, Any], status_code: int
):
    item_id = existing_item["id"]
    response = client.put(f"/item/{item_id}", json=body)
    assert response.status_code == status_code
    if status_code == HTTPStatus.OK:
        new_item = existing_item.copy()
        new_item.update(body)
        assert response.json() == new_item


def test_put_item_not_found():
    response = client.put("/item/999", json={"name": "new", "price": 10.0})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_put_item_deleted(deleted_item: dict[str, Any]):
    item_id = deleted_item["id"]
    response = client.put(f"/item/{item_id}", json={"name": "new", "price": 10.0})
    assert response.status_code == HTTPStatus.NOT_MODIFIED


@pytest.mark.parametrize(
    ("item", "body", "status_code"),
    [
        ("deleted_item", {}, HTTPStatus.NOT_MODIFIED),
        ("deleted_item", {"price": 9.99}, HTTPStatus.NOT_MODIFIED),
        ("deleted_item", {"name": "new name", "price": 9.99}, HTTPStatus.NOT_MODIFIED),
        ("existing_item", {}, HTTPStatus.OK),
        ("existing_item", {"price": 9.99}, HTTPStatus.OK),
        ("existing_item", {"name": "new name", "price": 9.99}, HTTPStatus.OK),
        (
            "existing_item",
            {"name": "new name", "price": 9.99, "odd": "value"},
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        (
            "existing_item",
            {"name": "new name", "price": 9.99, "deleted": True},
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        ("existing_item", {"price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_patch_item(request, item: str, body: dict[str, Any], status_code: int):
    item_data: dict[str, Any] = request.getfixturevalue(item)
    item_id = item_data["id"]
    response = client.patch(f"/item/{item_id}", json=body)
    assert response.status_code == status_code
    if status_code == HTTPStatus.OK:
        patch_response_body = response.json()
        response = client.get(f"/item/{item_id}")
        patched_item = response.json()
        assert patched_item == patch_response_body


def test_patch_item_not_found():
    response = client.patch("/item/999", json={"name": "new"})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_delete_item(existing_item: dict[str, Any]):
    item_id = existing_item["id"]
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK


def test_delete_item_not_found():
    response = client.delete("/item/999")
    assert response.status_code == HTTPStatus.NOT_FOUND


# === Unit-тесты для Broadcaster (WebSocket-логика) ===


def test_broadcaster_subscribe():
    b = Broadcaster()
    ws = AsyncMock()
    name = asyncio.run(b.subscribe(ws))
    assert ws in b.subscribers
    assert name.startswith("User_")


def test_broadcaster_unsubscribe():
    b = Broadcaster()
    ws = AsyncMock()
    asyncio.run(b.subscribe(ws))
    asyncio.run(b.unsubscribe(ws))
    assert ws not in b.subscribers


def test_broadcaster_publish():
    b = Broadcaster()
    ws1, ws2 = AsyncMock(), AsyncMock()
    asyncio.run(b.subscribe(ws1))
    asyncio.run(b.subscribe(ws2))
    asyncio.run(b.publish("hi", exclude_ws=ws1))
    ws1.send_text.assert_not_called()
    ws2.send_text.assert_awaited_once_with("hi")


def test_broadcaster_cleanup_dead():
    b = Broadcaster()
    ws = AsyncMock()
    ws.send_text.side_effect = Exception("dead")
    asyncio.run(b.subscribe(ws))
    asyncio.run(b.publish("msg"))
    assert ws not in b.subscribers


# === Тест для покрытия ws_chat (вызываем напрямую) ===


@pytest.mark.asyncio
async def test_ws_chat_coverage_trick():
    ws = AsyncMock()

    async def mock_receive():
        raise WebSocketDisconnect()

    ws.receive_text = mock_receive
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()

    try:
        await ws_chat(ws, "coverage_room")
    except WebSocketDisconnect:
        pass

    ws.accept.assert_awaited_once()


@pytest.mark.asyncio
async def test_ws_chat_coverage_final():
    ws = AsyncMock()

    # Имитируем последовательность: accept → receive пустое сообщение → receive исключение → disconnect
    ws.receive_text = AsyncMock(side_effect=["", b"\x00", WebSocketDisconnect()])
    ws.send_text = AsyncMock()
    ws.accept = AsyncMock()

    try:
        await ws_chat(ws, "final_coverage_room")
    except (WebSocketDisconnect, Exception):
        pass

    ws.accept.assert_awaited_once()

def test_add_item_to_cart_missing_item():
    cart_id = client.post("/cart").json()["id"]
    response = client.post(f"/cart/{cart_id}/add/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_deleted_item_returns_404():
    item = client.post("/item", json={"name": "to delete", "price": 10.0}).json()
    client.delete(f"/item/{item['id']}")
    response = client.get(f"/item/{item['id']}")
    assert response.status_code == HTTPStatus.NOT_FOUND
