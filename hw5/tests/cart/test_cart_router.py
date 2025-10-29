from http import HTTPStatus
from typing import Any
import pytest
from shop_api.item.store.schemas import ItemInfo
from fastapi.testclient import TestClient
from shop_api.item.store import queries as item_queries


@pytest.fixture
def sample_item(session):
    info = ItemInfo(name="TestItem", price=50.0)
    return item_queries.add(session, info)


def test_post_cart(client):
    response = client.post("/cart/")
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["price"] == 0
    assert data["items"] == []


def test_get_cart_by_id(client):
    # Сначала создаем корзину
    post = client.post("/cart/")
    cart_id = post.json()["id"]

    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cart_id


@pytest.mark.parametrize(
    ("query", "status_code"),
    [
        ({}, HTTPStatus.OK),
        ({"offset": 1, "limit": 2}, HTTPStatus.OK),
        ({"min_price": 1000.0}, HTTPStatus.OK),
        ({"max_price": 20.0}, HTTPStatus.OK),
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
def test_get_cart_list(client: TestClient, query: dict[str, Any], status_code: int):
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

        if "max_quantity" in query:
            assert quantity <= query["max_quantity"]


def test_get_cart_not_found(client):
    response = client.get("/cart/9999")
    assert response.status_code == 404


def test_add_item_to_cart(client, sample_item):
    post_cart = client.post("/cart/")
    cart_id = post_cart.json()["id"]
    item_id = sample_item.id

    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cart_id
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "TestItem"
    assert data["items"][0]["quantity"] == 1
