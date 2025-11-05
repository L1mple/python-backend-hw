import os
from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytest
from faker import Faker
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://shop_user:shop_password@localhost:5445/shop_db",
)

from shop_api.main import app

faker = Faker()

@pytest.fixture(scope="session")
def client():
    import asyncio
    from shop_api.database import init_db
    
    c = TestClient(app)
    c.__enter__()

    try:
        asyncio.run(init_db())
    except RuntimeError:
        pass
    
    try:
        yield c
    finally:
        c.__exit__(None, None, None)

@pytest.fixture(autouse=True)
def reset_before_test(client: TestClient):
    yield

@pytest.fixture()
def existing_empty_cart_id(client: TestClient) -> int:
    return client.post("/cart").json()["id"]


@pytest.fixture()
def existing_items(client: TestClient) -> list[int]:
    items = [
        {
            "name": f"Тестовый товар {i}",
            "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0),
        }
        for i in range(10)
    ]

    return [client.post("/item", json=item).json()["id"] for item in items]


@pytest.fixture()
def existing_not_empty_cart_id(
    client: TestClient,
    existing_empty_cart_id: int,
    existing_items: list[int],
) -> int:
    for item_id in faker.random_elements(existing_items, unique=False, length=3):
        client.post(f"/cart/{existing_empty_cart_id}/add/{item_id}")
    return existing_empty_cart_id


@pytest.fixture()
def existing_not_empty_carts(existing_items: list[int], client: TestClient) -> list[int]:
    carts: list[int] = []
    for i in range(20):
        cart_id: int = client.post("/cart").json()["id"]
        for item_id in faker.random_elements(existing_items, unique=False, length=i):
            client.post(f"/cart/{cart_id}/add/{item_id}")
        carts.append(cart_id)
    return carts


@pytest.fixture()
def existing_item(client: TestClient) -> dict[str, Any]:
    return client.post(
        "/item",
        json={
            "name": f"Тестовый товар {uuid4().hex}",
            "price": faker.pyfloat(min_value=10.0, max_value=100.0),
        },
    ).json()


@pytest.fixture()
def deleted_item(client: TestClient, existing_item: dict[str, Any]) -> dict[str, Any]:
    item_id = existing_item["id"]
    client.delete(f"/item/{item_id}")
    existing_item["deleted"] = True
    return existing_item

def test_post_cart(client: TestClient) -> None:
    response = client.post("/cart")
    assert response.status_code == HTTPStatus.CREATED
    assert "location" in response.headers
    assert "id" in response.json()


@pytest.mark.parametrize(
    ("cart_fixture", "not_empty"),
    [
        ("existing_empty_cart_id", False),
        ("existing_not_empty_cart_id", True),
    ],
)
def test_get_cart(client: TestClient, request, cart_fixture: str, not_empty: bool) -> None:
    cart_id = request.getfixturevalue(cart_fixture)
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == HTTPStatus.OK
    response_json = response.json()

    len_items = len(response_json["items"])
    assert len_items > 0 if not_empty else len_items == 0

    if not_empty:
        assert response_json["price"] > 0
        assert len(response_json["items"]) > 0
        assert isinstance(response_json["price"], (int, float))
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
def test_get_cart_list(
    client: TestClient,
    existing_not_empty_carts: list[int],
    query: dict[str, Any],
    status_code: int,
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

        quantity = sum(item["quantity"] for cart in data for item in cart["items"])

        if "min_quantity" in query:
            assert quantity >= query["min_quantity"]

        if "max_quantity" in query:
            assert quantity <= query["max_quantity"]

def test_post_item(client: TestClient) -> None:
    item = {"name": "test item", "price": 9.99}
    response = client.post("/item", json=item)

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()
    assert item["price"] == data["price"]
    assert item["name"] == data["name"]


def test_get_item(client: TestClient, existing_item: dict[str, Any]) -> None:
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
def test_get_item_list(
    client: TestClient,
    existing_items: list[int],
    query: dict[str, Any],
    status_code: int,
) -> None:
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
    client: TestClient,
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
    ("item_fixture", "body", "status_code"),
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
def test_patch_item(
    client: TestClient,
    request,
    item_fixture: str,
    body: dict[str, Any],
    status_code: int,
) -> None:
    item_data: dict[str, Any] = request.getfixturevalue(item_fixture)
    item_id = item_data["id"]
    response = client.patch(f"/item/{item_id}", json=body)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        patch_response_body = response.json()

        response = client.get(f"/item/{item_id}")
        patched_item = response.json()

        assert patched_item == patch_response_body


def test_delete_item(client: TestClient, existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]

    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK

    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND

    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK

def test_add_item_to_cart(client: TestClient) -> None:
    item = client.post("/item", json={"name": "TestItem", "price": 50.0}).json()
    cart_resp = client.post("/cart")
    cart_id = cart_resp.json()["id"]
    
    print(f"DEBUG: item_id={item['id']}, cart_id={cart_id}")
    
    response = client.post(f"/cart/{cart_id}/add/{item['id']}")
    print(f"DEBUG: response status={response.status_code}, body={response.json()}")
    assert response.status_code == HTTPStatus.OK
    
    cart_data = response.json()
    print(f"DEBUG: cart_data={cart_data}")
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["id"] == item["id"]
    assert cart_data["items"][0]["quantity"] == 1
    
    response = client.post(f"/cart/{cart_id}/add/{item['id']}")
    cart_data = response.json()
    assert cart_data["items"][0]["quantity"] == 2


def test_add_nonexistent_item_to_cart(client: TestClient) -> None:
    cart_id = client.post("/cart").json()["id"]
    
    response = client.post(f"/cart/{cart_id}/add/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND

def test_get_nonexistent_cart(client: TestClient) -> None:
    response = client.get("/cart/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_nonexistent_item(client: TestClient) -> None:
    response = client.get("/item/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_put_nonexistent_item(client: TestClient) -> None:
    response = client.put("/item/99999", json={"name": "test", "price": 1.0})
    assert response.status_code == HTTPStatus.NOT_FOUND

def test_cart_price_calculation(client: TestClient) -> None:
    item1 = client.post("/item", json={"name": "Item1", "price": 10.0}).json()
    item2 = client.post("/item", json={"name": "Item2", "price": 20.0}).json()
    cart_id = client.post("/cart").json()["id"]
    
    client.post(f"/cart/{cart_id}/add/{item1['id']}")
    client.post(f"/cart/{cart_id}/add/{item1['id']}")
    client.post(f"/cart/{cart_id}/add/{item2['id']}")
    
    cart = client.get(f"/cart/{cart_id}").json()
    assert cart["price"] == pytest.approx(40.0, 1e-8)


def test_deleted_item_not_in_price(client: TestClient) -> None:
    item = client.post("/item", json={"name": "Item", "price": 15.0}).json()
    cart_id = client.post("/cart").json()["id"]
    
    client.post(f"/cart/{cart_id}/add/{item['id']}")
    client.delete(f"/item/{item['id']}")
    
    cart = client.get(f"/cart/{cart_id}").json()
    assert cart["price"] == 0.0
    assert cart["items"][0]["available"] is False

def test_contracts_and_models():
    from shop_api.contracts import (
        ItemRequest,
        ItemResponse,
        PatchItemRequest,
        PutItemRequest,
        CartItemResponse,
        CartResponse,
    )
    from shop_api.models import ItemInfo, ItemEntity, CartItem, CartEntity, PatchItemInfo
    
    req = ItemRequest(name="Test", price=10.0)
    info = req.as_item_info()
    assert isinstance(info, ItemInfo)
    assert info.name == "Test"
    assert info.deleted is False
    
    entity = ItemEntity(id=1, info=ItemInfo(name="Test", price=10.0, deleted=False))
    resp = ItemResponse.from_entity(entity)
    assert resp.id == 1
    assert resp.name == "Test"
    
    patch = PatchItemRequest(name="New")
    patch_info = patch.as_patch_item_info()
    assert isinstance(patch_info, PatchItemInfo)
    assert patch_info.name == "New"
    
    put = PutItemRequest(name="Put", price=20.0)
    put_info = put.as_item_info()
    assert put_info.name == "Put"
    
    cart_item = CartItem(id=1, name="Item", quantity=2, available=True)
    cart_item_resp = CartItemResponse.from_cart_item(cart_item)
    assert cart_item_resp.id == 1
    assert cart_item_resp.quantity == 2
    
    cart_entity = CartEntity(id=1, items=[cart_item], price=20.0)
    cart_resp = CartResponse.from_entity(cart_entity)
    assert cart_resp.id == 1
    assert len(cart_resp.items) == 1

