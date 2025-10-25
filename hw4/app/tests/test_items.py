from http import HTTPStatus
from typing import Any

from fastapi.testclient import TestClient

def test_create_and_get_item(client: TestClient):
    r = client.post("/item", json={"name": "Apple", "price": 150.0})
    assert r.status_code == HTTPStatus.CREATED
    body = r.json()
    assert body["id"] > 0
    assert body["name"] == "Apple"
    assert body["price"] == 150.0
    assert body["deleted"] is False

    item_id = body["id"]
    r2 = client.get(f"/item/{item_id}")
    assert r2.status_code == HTTPStatus.OK
    assert r2.json()["name"] == "Apple"

def test_create_item_conflict(client: TestClient):
    assert client.post("/item", json={"name": "Dup", "price": 1}).status_code == HTTPStatus.CREATED
    r = client.post("/item", json={"name": "Dup", "price": 2})
    assert r.status_code == HTTPStatus.CONFLICT

def test_get_item_not_found(client: TestClient):
    r = client.get("/item/99999")
    assert r.status_code == HTTPStatus.NOT_FOUND

def test_list_items_filters_and_pagination(client: TestClient):
    for name, price in [("A", 50.0), ("B", 150.0), ("C", 250.0), ("D", 350.0)]:
        assert client.post("/item", json={"name": name, "price": price}).status_code == HTTPStatus.CREATED

    r = client.get("/item", params={"min_price": 100, "max_price": 200})
    names = [i["name"] for i in r.json()]
    assert names == ["B"]

    r2 = client.get("/item", params={"offset": 1, "limit": 2})
    names2 = [i["name"] for i in r2.json()]
    assert names2 == ["B", "C"]

def test_put_patch_and_delete_item(client: TestClient):
    r = client.post("/item", json={"name": "X", "price": 10.0})
    item_id = r.json()["id"]

    r2 = client.put(f"/item/{item_id}", json={"name": "X2", "price": 20.0})
    assert r2.status_code == HTTPStatus.OK
    assert r2.json()["name"] == "X2"
    assert r2.json()["price"] == 20.0

    r3 = client.patch(f"/item/{item_id}", json={"price": 30.0})
    assert r3.status_code == HTTPStatus.OK
    assert r3.json()["name"] == "X2"
    assert r3.json()["price"] == 30.0

    r4 = client.delete(f"/item/{item_id}")
    assert r4.status_code == HTTPStatus.NO_CONTENT

    r5 = client.get(f"/item/{item_id}")
    assert r5.status_code == HTTPStatus.OK
    assert r5.json()["deleted"] is True

    r6 = client.get("/item")
    ids = [i["id"] for i in r6.json()]
    assert item_id not in ids

    r7 = client.get("/item", params={"show_deleted": True})
    ids2 = [i["id"] for i in r7.json()]
    assert item_id in ids2

def test_put_patch_not_found_and_conflict(client: TestClient):
    assert client.put("/item/9999", json={"name": "no", "price": 1.0}).status_code == HTTPStatus.NOT_FOUND
    assert client.patch("/item/9999", json={"price": 1.0}).status_code == HTTPStatus.NOT_FOUND

    i1 = client.post("/item", json={"name": "N1", "price": 1.0}).json()["id"]
    i2 = client.post("/item", json={"name": "N2", "price": 2.0}).json()["id"]
    r = client.patch(f"/item/{i2}", json={"name": "N1"})
    assert r.status_code == HTTPStatus.CONFLICT

def test_validation_errors_items_list(client: TestClient):
    assert client.get("/item", params={"offset": -1}).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert client.get("/item", params={"limit": 0}).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert client.get("/item", params={"min_price": -1}).status_code == HTTPStatus.UNPROCESSABLE_ENTITY
