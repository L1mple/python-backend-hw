from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytest
from faker import Faker
from fastapi.testclient import TestClient

from shop_api.main import app
from tests.helpers import BaseItemFactory

client = TestClient(app)
faker = Faker()

@pytest.fixture()
def create_item_body():
    return BaseItemFactory.build().model_dump(mode="json")

@pytest.fixture()
def create_item():
    def create(price: float):
        json = BaseItemFactory.build(price=price).model_dump(mode="json")
        response = client.post("/item", json=json)
        return response.json()["id"]
    return create

def test_create_and_check_cart():
    response_post = client.post("/cart")
    assert response_post.status_code == 201

    cart_id = response_post.json()["id"]
    response_get = client.get(f"/cart/{cart_id}")
    assert response_get.status_code == 200
    assert response_get.json()["items"] == []

def test_create_get_item(create_item_body):
    response = client.post("/item", json=create_item_body)
    assert response.status_code == 201

    response = client.get(f"/item/{response.json()['id']}")
    assert response.status_code == 200

def test_add_item_to_cart(create_item_body):
    cart_id = client.post("/cart").json()["id"]
    item_id = client.post("/item", json=create_item_body).json()["id"]

    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.json()["price"] == create_item_body["price"]
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.json()["price"] == create_item_body["price"] * 2

    response = client.post(f"/cart/{cart_id}/add/{1000000}")
    assert response.status_code == 404

def test_delete_item(create_item_body):
    item_id = client.post("/item", json=create_item_body).json()["id"]
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 200

    get_deleted_response = client.get(f"/item/{item_id}")
    assert get_deleted_response.status_code == 404

def test_update_item(create_item_body):
    item_id = client.post("/item", json=create_item_body).json()["id"]

    put_response = client.put(f"/item/{item_id}", json={"name": "name", "price": 100.0})
    assert put_response.json()["name"] == "name"
    assert put_response.json()["price"] == 100.0

    patch_response = client.patch(f"item/{item_id}", json={"name": "updated", "price": 200.0})
    assert patch_response.json()["name"] == "updated"
    assert patch_response.json()["price"] == 200.0

    client.delete(f"/item/{item_id}")
    patch_response = client.patch(f"item/{item_id}", json={"name": "deleted"})
    assert patch_response.status_code == 304

def test_filter_items(create_item):
    create_item(price=3)
    create_item(price=8)
    item_id = create_item(price=12)
    client.delete(f"/item/{item_id}")

    response = client.get("/item", params={"max_price": 1})
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_filter_carts(create_item):
    item_id = create_item(price=12)
    cart_id = client.post("/cart").json()["id"]

    client.post(f"/cart/{cart_id}/add/{item_id}")
    response = client.get("/cart", params={"max_price": 13, "min_price": 10, "max_quantity": 2, "min_quantity": 1})
    assert response.status_code == 200
    assert len(response.json()) >= 1

    response = client.get("/cart", params={"max_price": 1, "min_quantity": 1000000})
    assert len(response.json()) == 0

    response = client.get("/cart", params={"max_quantity": 1, "min_price": 100000})
    assert len(response.json()) == 0

def test_not_found():
    get_response = client.get(f"/cart/{100000}")
    assert get_response.status_code == 404

    get_response = client.get(f"/item/{100000}")
    assert get_response.status_code == 404

    post_response = client.delete(f"/item/{100000}")
    assert post_response.status_code == 404

    patch_response = client.patch(f"item/{10000}", json={"name": "test"})
    assert patch_response.status_code == 404
