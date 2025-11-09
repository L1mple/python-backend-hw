from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytest
from faker import Faker
from fastapi.testclient import TestClient

from shop_api.main import app

client = TestClient(app)
faker = Faker()


@pytest.fixture()
def existing_empty_cart_id() -> int:
    return client.post("/cart").json()["id"]


@pytest.fixture(scope="session")
def existing_items() -> list[int]:
    items = [
        {
            "name": f"Тестовый товар {i}",
            "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0),
        }
        for i in range(10)
    ]

    return [client.post("/item", json=item).json()["id"] for item in items]


@pytest.fixture(scope="session", autouse=True)
def existing_not_empty_carts(existing_items: list[int]) -> list[int]:
    carts = []

    for i in range(20):
        cart_id: int = client.post("/cart").json()["id"]
        for item_id in faker.random_elements(existing_items, unique=False, length=i):
            client.post(f"/cart/{cart_id}/add/{item_id}")

        carts.append(cart_id)

    return carts


@pytest.fixture()
def existing_not_empty_cart_id(
    existing_empty_cart_id: int,
    existing_items: list[int],
) -> int:
    for item_id in faker.random_elements(existing_items, unique=False, length=3):
        client.post(f"/cart/{existing_empty_cart_id}/add/{item_id}")

    return existing_empty_cart_id


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


def test_post_cart() -> None:
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
def test_get_cart(request, cart: int, not_empty: bool) -> None:
    cart_id = request.getfixturevalue(cart)

    response = client.get(f"/cart/{cart_id}")

    assert response.status_code == HTTPStatus.OK
    response_json = response.json()

    len_items = len(response_json["items"])
    assert len_items > 0 if not_empty else len_items == 0

    if not_empty:
        price = 0

        for item in response_json["items"]:
            item_id = item["id"]
            price += client.get(f"/item/{item_id}").json()["price"] * item["quantity"]

        assert response_json["price"] == pytest.approx(price, 1e-8)
    else:
        assert response_json["price"] == 0.0


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
def test_get_cart_list(query: dict[str, Any], status_code: int):
    response = client.get("/cart", params=query)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        data = response.json()

        assert isinstance(data, list)

        if "min_price" in query:
            assert all(item["price"] >= query["min_price"] for item in data)

        if "max_price" in query:
            assert all(item["price"] <= query["max_price"] for item in data)

        quantity = sum(item["quantity"] for cart in data for item in cart["items"])

        if "min_quantity" in query:
            assert quantity >= query["min_quantity"]

        if "max_quantity" in query:
            assert quantity <= query["max_quantity"]


def test_post_item() -> None:
    item = {"name": "test item", "price": 9.99}
    response = client.post("/item", json=item)

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()
    assert item["price"] == data["price"]
    assert item["name"] == data["name"]


def test_get_item(existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]

    response = client.get(f"/item/{item_id}")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == existing_item


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
def test_get_item_list(query: dict[str, Any], status_code: int) -> None:
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


@pytest.mark.parametrize(
    ("body", "status_code"),
    [
        ({}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"price": 9.99}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"name": "new name", "price": 9.99}, HTTPStatus.OK),
    ],
)
def test_put_item(
    existing_item: dict[str, Any],
    body: dict[str, Any],
    status_code: int,
) -> None:
    item_id = existing_item["id"]
    response = client.put(f"/item/{item_id}", json=body)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        new_item = existing_item.copy()
        new_item.update(body)
        assert response.json() == new_item


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
    ],
)
def test_patch_item(request, item: str, body: dict[str, Any], status_code: int) -> None:
    item_data: dict[str, Any] = request.getfixturevalue(item)
    item_id = item_data["id"]
    response = client.patch(f"/item/{item_id}", json=body)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        patch_response_body = response.json()

        response = client.get(f"/item/{item_id}")
        patched_item = response.json()

        assert patched_item == patch_response_body


def test_delete_item(existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]

    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK

    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND

    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK


def test_add_to_cart_new_item(
    existing_empty_cart_id: int,
    existing_items: list[int],
) -> None:
    cart_id = existing_empty_cart_id
    item_id = existing_items[0]

    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    
    assert response.status_code == HTTPStatus.OK
    cart_data = response.json()
    assert cart_data["id"] == cart_id
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["id"] == item_id
    assert cart_data["items"][0]["quantity"] == 1


def test_add_to_cart_existing_item(
    existing_empty_cart_id: int,
    existing_items: list[int],
) -> None:
    cart_id = existing_empty_cart_id
    item_id = existing_items[0]

    client.post(f"/cart/{cart_id}/add/{item_id}")
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    
    assert response.status_code == HTTPStatus.OK
    cart_data = response.json()
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["quantity"] == 2


def test_add_to_cart_not_found_cart() -> None:
    response = client.post("/cart/99999/add/1")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_to_cart_not_found_item(existing_empty_cart_id: int) -> None:
    response = client.post(f"/cart/{existing_empty_cart_id}/add/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_item_not_found() -> None:
    response = client.get("/item/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_put_item_not_found() -> None:
    response = client.put("/item/99999", json={"name": "test", "price": 10.0})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_patch_item_not_found() -> None:
    response = client.patch("/item/99999", json={"price": 10.0})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_cart_not_found() -> None:
    response = client.get("/cart/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_list_carts_with_filters(
    existing_not_empty_carts: list[int],
) -> None:
    response = client.get("/cart", params={"min_quantity": 5})
    assert response.status_code == HTTPStatus.OK
    carts = response.json()
    for cart in carts:
        total_quantity = sum(item["quantity"] for item in cart["items"])
        assert total_quantity >= 5

    response = client.get("/cart", params={"max_quantity": 3})
    assert response.status_code == HTTPStatus.OK
    carts = response.json()
    for cart in carts:
        total_quantity = sum(item["quantity"] for item in cart["items"])
        assert total_quantity <= 3


def test_list_items_with_deleted(existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]
    
    client.delete(f"/item/{item_id}")
    
    response = client.get("/item", params={"limit": 100})
    assert response.status_code == HTTPStatus.OK
    items = response.json()
    item_ids = [item["id"] for item in items]
    assert item_id not in item_ids
    
    response = client.get("/item", params={"show_deleted": True, "limit": 100})
    assert response.status_code == HTTPStatus.OK
    items = response.json()
    item_ids = [item["id"] for item in items]
    assert item_id in item_ids


def test_cart_price_calculation(
    existing_empty_cart_id: int,
    existing_items: list[int],
) -> None:
    cart_id = existing_empty_cart_id
    
    for item_id in existing_items[:3]:
        client.post(f"/cart/{cart_id}/add/{item_id}")
    
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == HTTPStatus.OK
    cart = response.json()
    
    calculated_price = 0.0
    for item in cart["items"]:
        item_response = client.get(f"/item/{item['id']}")
        item_data = item_response.json()
        calculated_price += item_data["price"] * item["quantity"]
    
    assert cart["price"] == pytest.approx(calculated_price, 1e-8)


def test_create_item_validation() -> None:
    response = client.post("/item", json={"name": "test", "price": -10.0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    
    response = client.post("/item", json={"name": "test", "price": 0.0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    
    response = client.post("/item", json={"name": "", "price": 10.0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_list_items_offset_limit() -> None:
    response1 = client.get("/item", params={"offset": 0, "limit": 5})
    response2 = client.get("/item", params={"offset": 5, "limit": 5})
    
    assert response1.status_code == HTTPStatus.OK
    assert response2.status_code == HTTPStatus.OK
    
    items1 = response1.json()
    items2 = response2.json()
    
    ids1 = [item["id"] for item in items1]
    ids2 = [item["id"] for item in items2]
    
    assert len(set(ids1) & set(ids2)) == 0


def test_websocket_chat() -> None:
    with client.websocket_connect("/chat/test-room") as websocket1:
        with client.websocket_connect("/chat/test-room") as websocket2:
            websocket1.send_text("Hello from client 1")
            
            data = websocket2.receive_text()
            assert "Hello from client 1" in data
            
            websocket2.send_text("Hello from client 2")
            
            data = websocket1.receive_text()
            assert "Hello from client 2" in data


def test_websocket_multiple_rooms() -> None:
    with client.websocket_connect("/chat/room1") as ws_room1:
        with client.websocket_connect("/chat/room2") as ws_room2:
            ws_room1.send_text("Message for room1")
            ws_room2.send_text("Message for room2")
