import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from shop_api.routers import carts
from shop_api.storage.memory import _carts, _items, _next_cart_id, _lock
from shop_api.schemas.cart import Cart, CartItem

app = FastAPI()
app.include_router(carts.router)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_memory():
    global _carts, _items, _next_cart_id, _lock
    _carts.clear()
    _items.clear()
    _next_cart_id = 1
    _lock = _lock.__class__() 
    _items[1] = type("Item", (), {"name": "Item1", "price": 10.0, "deleted": False})()
    yield
    _carts.clear()
    _items.clear()
    _next_cart_id = 1


def mock_compute_cart(cart_id: int):
    if cart_id not in _carts:
        raise KeyError
    bag = _carts[cart_id]
    items_out = []
    total = 0.0
    for iid, qty in bag.items():
        item = _items[iid]
        items_out.append(CartItem(
            id=iid,
            name=item.name,
            quantity=qty,
            available=not item.deleted
        ))
        if not item.deleted:
            total += item.price * qty
    return Cart(id=cart_id, items=items_out, price=total)


def test_create_cart():
    response = client.post("/cart/")
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert response.headers["Location"] == f"/cart/{data['id']}"
    assert data["id"] in _carts


def test_get_cart_success(monkeypatch):
    _carts[1] = {}
    monkeypatch.setattr("shop_api.utils.cart_utils.compute_cart", mock_compute_cart)
    response = client.get("/cart/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert isinstance(data["items"], list)
    assert data["price"] == 0.0


def test_get_cart_not_found():
    response = client.get("/cart/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "cart not found"}


def test_list_carts_filters(monkeypatch):
    _carts[1] = {1: 2}
    _carts[2] = {1: 5}

    monkeypatch.setattr("shop_api.utils.cart_utils.compute_cart", mock_compute_cart)

    resp = client.get("/cart/")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = client.get("/cart/?min_price=30")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == 2

    resp = client.get("/cart/?max_price=20")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == 1

    resp = client.get("/cart/?min_quantity=3")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == 2

    resp = client.get("/cart/?max_quantity=3")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == 1

    resp = client.get("/cart/?offset=1&limit=1")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == 2


def test_add_item_success(monkeypatch):
    _carts[1] = {}
    monkeypatch.setattr("shop_api.utils.cart_utils.compute_cart", mock_compute_cart)
    response = client.post("/cart/1/add/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["items"][0]["quantity"] == 1
    assert _carts[1][1] == 1


def test_add_item_cart_not_found():
    response = client.post("/cart/999/add/1")
    assert response.status_code == 404
    assert response.json() == {"detail": "cart not found"}


def test_add_item_item_not_found():
    _carts[1] = {}
    response = client.post("/cart/1/add/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "item not found"}
