from http import HTTPStatus

from fastapi.testclient import TestClient

from shop_api.main import app


client = TestClient(app)


def test_get_nonexistent_cart() -> None:
    response = client.get("/cart/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_to_nonexistent_cart() -> None:
    # create an item
    item = client.post("/item", json={"name": "x", "price": 1.0}).json()
    response = client.post(f"/cart/999999/add/{item['id']}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_nonexistent_item_to_cart() -> None:
    # create a cart
    cart_id = client.post("/cart").json()["id"]
    response = client.post(f"/cart/{cart_id}/add/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_put_deleted_item_returns_404() -> None:
    item = client.post("/item", json={"name": "y", "price": 2.0}).json()
    item_id = item["id"]
    client.delete(f"/item/{item_id}")
    response = client.put(f"/item/{item_id}", json={"name": "z", "price": 3.0})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_patch_nonexistent_item_returns_404() -> None:
    response = client.patch("/item/999999", json={})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_nonexistent_item_returns_404() -> None:
    response = client.get("/item/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


