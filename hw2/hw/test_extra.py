from http import HTTPStatus

from fastapi.testclient import TestClient

from shop_api.main import app


client = TestClient(app)


def _create_item(name: str = "x", price: float = 1.0) -> dict:
    return client.post("/item", json={"name": name, "price": price}).json()


def _create_cart() -> int:
    return client.post("/cart").json()["id"]


def test_get_item_not_found() -> None:
    response = client.get("/item/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_cart_not_found() -> None:
    response = client.get("/cart/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_item_to_cart_not_found_cart() -> None:
    item = _create_item()
    response = client.post(f"/cart/999999/add/{item['id']}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_item_to_cart_not_found_item() -> None:
    cart_id = _create_cart()
    response = client.post(f"/cart/{cart_id}/add/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_put_item_deleted() -> None:
    item = _create_item()
    client.delete(f"/item/{item['id']}")
    response = client.put(f"/item/{item['id']}", json={"name": "x", "price": 1.0})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_patch_item_not_found() -> None:
    response = client.patch("/item/999999", json={"name": "x"})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_list_items_excludes_deleted_by_default() -> None:
    item = _create_item()
    client.delete(f"/item/{item['id']}")
    response = client.get("/item")
    assert response.status_code == HTTPStatus.OK
    ids = {it["id"] for it in response.json()}
    assert item["id"] not in ids


def test_metrics_endpoint_available() -> None:
    response = client.get("/metrics")
    assert response.status_code == HTTPStatus.OK
    assert "python_info" in response.text or "http_requests_total" in response.text

