from http import HTTPStatus
from fastapi.testclient import TestClient

def create_item(client: TestClient, name: str, price: float) -> int:
    return client.post("/item", json={"name": name, "price": price}).json()["id"]

def create_cart(client: TestClient) -> int:
    return client.post("/cart").json()["id"]

def test_create_and_get_empty_cart(client: TestClient):
    cart_id = create_cart(client)
    r = client.get(f"/cart/{cart_id}")
    assert r.status_code == HTTPStatus.OK
    body = r.json()
    assert body["id"] == cart_id
    assert body["total_price"] == 0.0
    assert body["total_quantity"] == 0
    assert body["items"] == []

def test_add_to_cart_and_increment(client: TestClient):
    item_id = create_item(client, "Apple", 100.0)
    cart_id = create_cart(client)

    r1 = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert r1.status_code == HTTPStatus.OK
    r2 = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert r2.status_code == HTTPStatus.OK

    cart = client.get(f"/cart/{cart_id}").json()
    assert cart["total_quantity"] == 2
    assert cart["total_price"] == 200.0
    assert cart["items"][0]["quantity"] == 2

def test_add_deleted_item_returns_404(client: TestClient):
    item_id = create_item(client, "X", 10.0)
    assert client.delete(f"/item/{item_id}").status_code == HTTPStatus.NO_CONTENT
    cart_id = create_cart(client)
    r = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert r.status_code == HTTPStatus.NOT_FOUND

def test_cart_list_filters_and_pagination(client: TestClient):
    p = create_item(client, "P", 100.0)
    q = create_item(client, "Q", 200.0)

    c1 = create_cart(client)
    c2 = create_cart(client)

    assert client.post(f"/cart/{c1}/add/{p}").status_code == HTTPStatus.OK
    assert client.post(f"/cart/{c2}/add/{q}").status_code == HTTPStatus.OK
    assert client.post(f"/cart/{c2}/add/{q}").status_code == HTTPStatus.OK

    r1 = client.get("/cart", params={"min_price": 200})
    ids1 = [c["id"] for c in r1.json()]
    assert ids1 == [c2]

    r2 = client.get("/cart", params={"max_quantity": 1})
    ids2 = [c["id"] for c in r2.json()]
    assert ids2 == [c1]

    r3 = client.get("/cart", params={"limit": 1})
    assert [c["id"] for c in r3.json()] == [c1]
    r4 = client.get("/cart", params={"offset": 1, "limit": 1})
    assert [c["id"] for c in r4.json()] == [c2]

def test_get_cart_not_found(client: TestClient):
    assert client.get("/cart/99999").status_code == HTTPStatus.NOT_FOUND

def test_validation_errors_carts_list(client: TestClient):
    assert client.get("/cart", params={"offset": -1}).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert client.get("/cart", params={"limit": 0}).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert client.get("/cart", params={"min_quantity": -1}).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert client.get("/cart", params={"min_price": -1}).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
