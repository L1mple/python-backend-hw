import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from shop_api.routers import items
from shop_api.storage.memory import _items, _next_item_id, _lock

app = FastAPI()
app.include_router(items.router)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_memory():
    global _items, _next_item_id, _lock
    _items.clear()
    _next_item_id = 1
    _lock = _lock.__class__()
    yield
    _items.clear()
    _next_item_id = 1


def test_create_item():
    payload = {"name": "TestItem", "price": 100.0}
    resp = client.post("/item/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "TestItem"
    assert data["price"] == 100.0
    assert 1 in _items


def test_get_item_success():
    _items[1] = type("Item", (), {"id": 1, "name": "Item1", "price": 10.0, "deleted": False})()
    resp = client.get("/item/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["name"] == "Item1"


def test_get_item_not_found():
    resp = client.get("/item/999")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "item not found"}

    # помеченный как deleted
    _items[1] = type("Item", (), {"id": 1, "name": "Item1", "price": 10.0, "deleted": True})()
    resp = client.get("/item/1")
    assert resp.status_code == 404


def test_list_items_filters():
    # создаем 3 элемента
    _items[1] = type("Item", (), {"id": 1, "name": "A", "price": 10, "deleted": False})()
    _items[2] = type("Item", (), {"id": 2, "name": "B", "price": 20, "deleted": False})()
    _items[3] = type("Item", (), {"id": 3, "name": "C", "price": 30, "deleted": True})()

    # без фильтров, show_deleted=False
    resp = client.get("/item/")
    data = resp.json()
    assert len(data) == 2  # не учитываем deleted

    # show_deleted=True
    resp = client.get("/item/?show_deleted=true")
    data = resp.json()
    assert len(data) == 3

    # min_price
    resp = client.get("/item/?min_price=15")
    data = resp.json()
    assert all(d["price"] >= 15 for d in data)

    # max_price
    resp = client.get("/item/?max_price=15")
    data = resp.json()
    assert all(d["price"] <= 15 for d in data)

    # offset & limit
    resp = client.get("/item/?offset=1&limit=1")
    data = resp.json()
    assert len(data) == 1


def test_replace_item_success():
    _items[1] = type("Item", (), {"id": 1, "name": "Old", "price": 10.0, "deleted": False})()
    payload = {"name": "NewName", "price": 99.0}
    resp = client.put("/item/1", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "NewName"
    assert data["price"] == 99.0


def test_replace_item_not_found():
    payload = {"name": "X", "price": 1.0}
    resp = client.put("/item/999", json=payload)
    assert resp.status_code == 404


def test_patch_item_success():
    _items[1] = type("Item", (), {"id": 1, "name": "Old", "price": 10.0, "deleted": False})()
    resp = client.patch("/item/1", json={"name": "New"})
    assert resp.status_code == 200
    assert _items[1].name == "New"

    resp = client.patch("/item/1", json={"price": 50})
    assert resp.status_code == 200
    assert _items[1].price == 50

    resp = client.patch("/item/1", json={"name": "Final", "price": 100})
    assert resp.status_code == 200
    assert _items[1].name == "Final"
    assert _items[1].price == 100


def test_patch_item_not_found():
    resp = client.patch("/item/999", json={"name": "X"})
    assert resp.status_code == 404


def test_patch_item_deleted():
    _items[1] = type("Item", (), {"id": 1, "name": "X", "price": 10.0, "deleted": True})()
    resp = client.patch("/item/1", json={"name": "Y"})
    assert resp.status_code == 304


def test_patch_item_invalid_field():
    _items[1] = type("Item", (), {"id": 1, "name": "X", "price": 10.0, "deleted": False})()
    resp = client.patch("/item/1", json={"invalid": 123})
    assert resp.status_code == 422

    resp = client.patch("/item/1", json={"price": -10})
    assert resp.status_code == 422


def test_delete_item():
    # элемент существует
    _items[1] = type("Item", (), {"id": 1, "name": "X", "price": 10.0, "deleted": False})()
    resp = client.delete("/item/1")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert _items[1].deleted is True

    # элемент не существует
    resp = client.delete("/item/999")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
