from http import HTTPStatus
from typing import Any
from uuid import uuid4
from unittest.mock import patch

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
            price += client.get(f"/item/{item_id}").json()[
                "price"] * item["quantity"]

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

        quantity = sum(item["quantity"]
                       for cart in data for item in cart["items"])

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
        ("deleted_item", {"name": "new name",
         "price": 9.99}, HTTPStatus.NOT_MODIFIED),
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


def test_get_cart_not_found() -> None:
    response = client.get("/cart/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "cart not found" in response.json()["detail"]


def test_add_to_cart_success(existing_item: dict[str, Any]) -> None:
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]
    item_id = existing_item["id"]
    response = client.post(f"/cart/{cart_id}/add/{item_id}")

    assert response.status_code == HTTPStatus.OK
    cart_data = response.json()
    assert cart_data["id"] == cart_id
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["id"] == item_id
    assert cart_data["items"][0]["quantity"] == 1
    assert cart_data["price"] == existing_item["price"]


def test_add_to_cart_multiple_times(existing_item: dict[str, Any]) -> None:
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]
    item_id = existing_item["id"]

    for i in range(1, 4):
        response = client.post(f"/cart/{cart_id}/add/{item_id}")
        assert response.status_code == HTTPStatus.OK

        cart_data = response.json()
        assert len(cart_data["items"]) > 0, \
            f"Cart is empty after adding item {i} times"
        assert cart_data["items"][0]["quantity"] == i
        assert cart_data["price"] == existing_item["price"] * i


def test_add_to_nonexistent_cart(existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]
    response = client.post(f"/cart/999999/add/{item_id}")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "cart or item not found" in response.json()["detail"]


def test_add_nonexistent_item_to_cart() -> None:
    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]

    response = client.post(f"/cart/{cart_id}/add/999999")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "cart or item not found" in response.json()["detail"]


def test_cart_with_multiple_different_items() -> None:
    items = []
    for i in range(3):
        item_response = client.post(
            "/item",
            json={
                "name": f"Test item {i}",
                "price": 10.0 * (i + 1),
            },
        )
        items.append(item_response.json())

    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]

    total_price = 0.0
    total_quantity = 0

    for i, item in enumerate(items):
        quantity = i + 2
        for _ in range(quantity):
            client.post(f"/cart/{cart_id}/add/{item['id']}")

        total_price += item["price"] * quantity
        total_quantity += quantity

    response = client.get(f"/cart/{cart_id}")
    cart_data = response.json()

    assert len(cart_data["items"]) == 3
    assert cart_data["price"] == pytest.approx(total_price, 1e-8)
    assert cart_data["quantity"] == total_quantity


@pytest.mark.parametrize(
    ("filters", "is_results"),
    [
        ({}, True),
        ({"offset": 0, "limit": 1}, True),
        ({"min_price": 0.0}, True),
        ({"max_price": 10000.0}, True),
        ({"min_quantity": 0}, True),
        ({"max_quantity": 1000}, True),
        ({"min_price": 100000.0}, False),
        ({"max_price": 0.01}, False),
        ({"min_quantity": 1000}, False),
        ({"max_quantity": 0}, False),
    ],
)
def test_list_carts_filtering(
    filters: dict[str, Any],
    is_results: bool,
) -> None:
    response = client.get("/cart", params=filters)
    assert response.status_code == HTTPStatus.OK

    carts = response.json()

    if is_results:
        if "min_price" in filters:
            for cart in carts:
                assert cart["price"] >= filters["min_price"]

        if "max_price" in filters:
            for cart in carts:
                assert cart["price"] <= filters["max_price"]

        if "min_quantity" in filters:
            for cart in carts:
                assert cart["quantity"] >= filters["min_quantity"]

        if "max_quantity" in filters:
            for cart in carts:
                assert cart["quantity"] <= filters["max_quantity"]

    if "limit" in filters:
        assert len(carts) <= filters["limit"]


def test_add_to_cart_deleted_item() -> None:
    item_response = client.post(
        "/item",
        json={
            "name": "Item to be deleted",
            "price": 25.0,
        },
    )
    item = item_response.json()

    client.delete(f"/item/{item['id']}")

    cart_response = client.post("/cart")
    cart_id = cart_response.json()["id"]

    response = client.post(f"/cart/{cart_id}/add/{item['id']}")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "item deleted" in response.json()["detail"]


def test_get_cart_skips_missing_and_deleted_items() -> None:
    cart_id = client.post("/cart").json()["id"]

    with patch(
        "shop_api.handlers.cart.psql_get_cart"
    ) as mock_get_cart, patch(
        "shop_api.handlers.cart.psql_get_items_by_ids"
    ) as mock_get_items:
        mock_get_cart.return_value = {7: 2, 9: 1}
        mock_get_items.return_value = [
            {
                "id": 7,
                "name": "Old item",
                "price": 10.0,
                "description": None,
                "deleted": True,
            }
        ]

        response = client.get(f"/cart/{cart_id}")

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["items"] == []
    assert data["price"] == 0.0
    assert data["quantity"] == 0


def test_put_item_not_found() -> None:
    response = client.put(
        "/item/999999",
        json={"name": "n", "price": 1.0},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"]["error"] == "item not found"


def test_patch_item_not_found_initial() -> None:
    response = client.patch("/item/999999", json={"price": 2.0})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"]["error"] == "item not found"


def test_patch_item_not_found_after_update() -> None:
    with patch("shop_api.handlers.item.psql_get_item") as mock_get, patch(
        "shop_api.handlers.item.psql_patch_item"
    ) as mock_patch:
        mock_get.return_value = {
            "id": 1,
            "name": "n",
            "price": 1.0,
            "deleted": False,
        }
        mock_patch.return_value = None

        response = client.patch("/item/1", json={"price": 2.0})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"]["error"] == "item not found"


def test_delete_item_not_found() -> None:
    response = client.delete("/item/999999")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"]["error"] == "item not found"
