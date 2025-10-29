from http import HTTPStatus
from typing import Any

from fastapi.testclient import TestClient
import pytest


def test_post_item(client):
    payload = {"name": "Book", "price": 20.5, "deleted": False}
    response = client.post("/item/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["price"] == payload["price"]
    assert data["deleted"] == payload["deleted"]


def test_get_item_by_id(client):
    payload = {"name": "Book2", "price": 15.0}
    post = client.post("/item/", json=payload)
    item_id = post.json()["id"]

    response = client.get(f"/item/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id


def test_get_item_not_found(client):
    response = client.get("/item/9999")
    assert response.status_code == 404


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
def test_get_item_list(client: TestClient, query: dict[str, Any], status_code: int) -> None:
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


def test_patch_item(client):
    payload = {"name": "Book3", "price": 10.0}
    post = client.post("/item/", json=payload)
    item_id = post.json()["id"]

    patch_payload = {"price": 12.0}
    response = client.patch(f"/item/{item_id}", json=patch_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["price"] == 12.0


def test_put_item(client):
    payload = {"name": "Book4", "price": 5.0}
    post = client.post("/item/", json=payload)
    item_id = post.json()["id"]

    put_payload = {"name": "Book4_updated", "price": 6.0, "deleted": False}
    response = client.put(f"/item/{item_id}", json=put_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Book4_updated"
    assert data["price"] == 6.0


def test_delete_item(client):
    payload = {"name": "Book5", "price": 8.0}
    post = client.post("/item/", json=payload)
    item_id = post.json()["id"]

    response = client.delete(f"/item/{item_id}")
    assert response.status_code == 204

    response2 = client.get(f"/item/{item_id}")
    assert response2.status_code == 404


def test_patch_item_not_found(client):
    response = client.patch("/item/9999", json={"price": 50})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_put_item_not_found(client):
    response = client.put("/item/9999", json={"name": "Nope", "price": 99.9, "deleted": False})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_item_not_found(client):
    response = client.delete("/item/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
