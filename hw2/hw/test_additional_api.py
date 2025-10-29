from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from shop_api.main import app


client = TestClient(app)


def test_get_unknown_item_returns_404():
    resp = client.get("/item/999999")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_add_item_and_fetch_list_filters_min_max_price_and_pagination():
    # Create several items
    ids = []
    for i in range(5):
        r = client.post("/item", json={"name": f"it{i}", "price": 10.0 + i})
        assert r.status_code == HTTPStatus.CREATED
        ids.append(r.json()["id"])

    # min_price
    r = client.get("/item", params={"min_price": 12.0})
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert all(item["price"] >= 12.0 for item in data)

    # max_price
    r = client.get("/item", params={"max_price": 12.0})
    assert r.status_code == HTTPStatus.OK
    data = r.json()
    assert all(item["price"] <= 12.0 for item in data)

    # pagination
    r1 = client.get("/item", params={"offset": 0, "limit": 2})
    r2 = client.get("/item", params={"offset": 2, "limit": 2})
    assert r1.status_code == HTTPStatus.OK and r2.status_code == HTTPStatus.OK
    assert isinstance(r1.json(), list) and isinstance(r2.json(), list)


def test_patch_rejects_extra_fields_and_deleted_field():
    # create
    r = client.post("/item", json={"name": "x", "price": 11.0})
    item = r.json()

    # extra field -> 422
    r = client.patch(f"/item/{item['id']}", json={"odd": "value"})
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    # deleted field not allowed -> 422
    r = client.patch(f"/item/{item['id']}", json={"deleted": True})
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_cart_unknown_returns_404():
    r = client.get("/cart/999999")
    assert r.status_code == HTTPStatus.NOT_FOUND


def test_add_nonexistent_item_to_cart_404():
    # create cart
    cart_id = client.post("/cart").json()["id"]
    r = client.post(f"/cart/{cart_id}/add/999999")
    assert r.status_code == HTTPStatus.NOT_FOUND


def test_cart_price_excludes_deleted_items():
    # create item and cart
    item_resp = client.post("/item", json={"name": "to-delete", "price": 33.0})
    item_id = item_resp.json()["id"]
    cart_id = client.post("/cart").json()["id"]

    # add and verify price
    client.post(f"/cart/{cart_id}/add/{item_id}")
    r = client.get(f"/cart/{cart_id}")
    assert r.status_code == HTTPStatus.OK
    assert r.json()["price"] == pytest.approx(33.0)

    # delete item and cart price should drop to 0
    client.delete(f"/item/{item_id}")
    r = client.get(f"/cart/{cart_id}")
    assert r.status_code == HTTPStatus.OK
    assert r.json()["price"] == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("params", "status"),
    [
        ({"offset": -5}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_item_list_validation_errors(params, status):
    r = client.get("/item", params=params)
    assert r.status_code == status


@pytest.mark.parametrize(
    ("params", "status"),
    [
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_quantity": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_quantity": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_cart_list_validation_errors(params, status):
    r = client.get("/cart", params=params)
    assert r.status_code == status


