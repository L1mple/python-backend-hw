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
def empty_cart_id() -> int:
    return client.post("/cart").json()["id"]

@pytest.fixture(scope="session")
def sample_items() -> list[int]:
    items = [
        {
            "name": f"Sample Product {i}",
            "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0),
        }
        for i in range(10)
    ]
    return [client.post("/item", json=item).json()["id"] for item in items]

@pytest.fixture(scope="session", autouse=True)
def populated_carts(sample_items: list[int]) -> list[int]:
    carts = []
    for i in range(15):
        cart_id: int = client.post("/cart").json()["id"]
        for item_id in faker.random_elements(sample_items, unique=False, length=i):
            client.post(f"/cart/{cart_id}/add/{item_id}")
        carts.append(cart_id)
    return carts

@pytest.fixture()
def cart_with_items(empty_cart_id: int, sample_items: list[int]) -> int:
    for item_id in faker.random_elements(sample_items, unique=False, length=3):
        client.post(f"/cart/{empty_cart_id}/add/{item_id}")
    return empty_cart_id

@pytest.fixture()
def sample_item() -> dict[str, Any]:
    return client.post(
        "/item",
        json={
            "name": f"Test Item {uuid4().hex}",
            "price": faker.pyfloat(min_value=10.0, max_value=100.0),
        },
    ).json()

@pytest.fixture()
def removed_item(sample_item: dict[str, Any]) -> dict[str, Any]:
    item_id = sample_item["id"]
    client.delete(f"/item/{item_id}")
    sample_item["deleted"] = True
    return sample_item

def test_create_cart() -> None:
    response = client.post("/cart")
    assert response.status_code == HTTPStatus.CREATED
    assert "location" in response.headers
    assert "id" in response.json()


@pytest.mark.parametrize(
    ("cart_fixture", "has_items"),
    [
        ("empty_cart_id", False),
        ("cart_with_items", True),
    ],
)
def test_retrieve_cart(request, cart_fixture: str, has_items: bool) -> None:
    cart_id = request.getfixturevalue(cart_fixture)
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    items_count = len(data["items"])
    assert items_count > 0 if has_items else items_count == 0

    if has_items:
        calculated_total = 0
        for item in data["items"]:
            item_data = client.get(f"/item/{item['id']}").json()
            calculated_total += item_data["price"] * item["quantity"]
        assert data["total_price"] == pytest.approx(calculated_total, 1e-8)
    else:
        assert data["total_price"] == 0.0

@pytest.mark.parametrize(
    ("params", "expected_status"),
    [
        ({}, HTTPStatus.OK),
        ({"offset": 1, "limit": 2}, HTTPStatus.OK),
        ({"min_price": 1000.0}, HTTPStatus.OK),
        ({"max_price": 20.0}, HTTPStatus.OK),
        ({"min_quantity": 1}, HTTPStatus.OK),
        ({"max_quantity": 0}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_list_carts(params: dict[str, Any], expected_status: int):
    response = client.get("/cart", params=params)
    assert response.status_code == expected_status

def test_create_item() -> None:
    item_data = {"name": "New Product", "price": 15.99}
    response = client.post("/item", json=item_data)
    assert response.status_code == HTTPStatus.CREATED
    result = response.json()
    assert item_data["price"] == result["price"]
    assert item_data["name"] == result["name"]

def test_get_item(sample_item: dict[str, Any]) -> None:
    item_id = sample_item["id"]
    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == sample_item

def test_update_item_full(sample_item: dict[str, Any]) -> None:
    item_id = sample_item["id"]
    update_data = {"name": "Updated Name", "price": 25.99}
    response = client.put(f"/item/{item_id}", json=update_data)
    assert response.status_code == HTTPStatus.OK
    updated = response.json()
    assert updated["name"] == update_data["name"]
    assert updated["price"] == update_data["price"]

def test_partial_update(sample_item: dict[str, Any]) -> None:
    item_id = sample_item["id"]
    patch_data = {"price": 19.99}
    response = client.patch(f"/item/{item_id}", json=patch_data)
    assert response.status_code == HTTPStatus.OK
    assert response.json()["price"] == 19.99

def test_remove_item(sample_item: dict[str, Any]) -> None:
    item_id = sample_item["id"]
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND

def test_invalid_cart_access():
    response = client.get("/cart/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND

def test_add_to_invalid_cart():
    response = client.post("/cart/99999/add/1")
    assert response.status_code == HTTPStatus.NOT_FOUND

def test_item_validation_errors():
    response = client.post("/item", json={"name": "test", "price": -10.0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

def test_cart_pagination():
    response = client.get("/cart", params={"offset": 0, "limit": 3})
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) <= 3

def test_put_nonexistent_item_returns_304():
    r = client.put("/item/999999", json={"name": "X", "price": 1.0})
    assert r.status_code == HTTPStatus.NOT_MODIFIED

def test_patch_nonexistent_item_returns_304():
    r = client.patch("/item/999998", json={"name": "Y"})
    assert r.status_code == HTTPStatus.NOT_MODIFIED

def test_patch_empty_body_no_changes(sample_item: dict[str, Any]):
    item_id = sample_item["id"]
    r = client.patch(f"/item/{item_id}", json={})
    assert r.status_code == HTTPStatus.OK
    r_get = client.get(f"/item/{item_id}")
    assert r_get.status_code == HTTPStatus.OK
    data = r_get.json()
    assert data["name"] == sample_item["name"]
    assert data["price"] == sample_item["price"]

def test_patch_sets_name_to_none(sample_item: dict[str, Any]):
    item_id = sample_item["id"]
    r = client.patch(f"/item/{item_id}", json={"name": None})
    assert r.status_code == HTTPStatus.OK
    r_get = client.get(f"/item/{item_id}")
    assert r_get.status_code == HTTPStatus.OK
    assert r_get.json()["name"] is None

def test_delete_nonexistent_item_is_noop_ok_true():
    r = client.delete("/item/123456789")
    assert r.status_code == HTTPStatus.OK
    assert r.json() == {"ok": True}

def test_add_to_cart_invalid_item_id(empty_cart_id: int):
    r = client.post(f"/cart/{empty_cart_id}/add/777777")
    assert r.status_code == HTTPStatus.NOT_FOUND

def test_list_items_filters_and_pagination():
    r1 = client.post("/item", json={"name": "AA", "price": 1.0})
    assert r1.status_code == HTTPStatus.CREATED
    id1 = r1.json()["id"]

    r2 = client.post("/item", json={"name": "BB", "price": 5.0})
    assert r2.status_code == HTTPStatus.CREATED
    id2 = r2.json()["id"]

    r_del = client.delete(f"/item/{id2}")
    assert r_del.status_code == HTTPStatus.OK

    r = client.get("/item", params={"min_price": 0.0, "max_price": 10.0})
    assert r.status_code == HTTPStatus.OK
    names = [x["name"] for x in r.json()]
    assert "AA" in names and "BB" not in names

    r = client.get("/item", params={"show_deleted": True})
    assert r.status_code == HTTPStatus.OK
    names = [x["name"] for x in r.json()]
    assert "AA" in names and "BB" in names

    r = client.get("/item", params={"show_deleted": True, "min_price": 4.9, "max_price": 5.1})
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert len(data) == 1 and data[0]["name"] == "BB" and data[0]["price"] == 5.0

    r = client.get("/item", params={"show_deleted": True, "offset": 0, "limit": 1})
    assert r.status_code == HTTPStatus.OK
    assert len(r.json()) == 1
