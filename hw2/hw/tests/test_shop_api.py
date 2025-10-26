import pytest
from fastapi.testclient import TestClient
from ..shop_api.main import app, items, carts, item_counter, cart_counter

@pytest.fixture(autouse=True)
def reset_state():
    items.clear()
    carts.clear()
    global item_counter, cart_counter
    item_counter = cart_counter = 0

@pytest.fixture()
def client():
    return TestClient(app)

def test_create_item(client):
    resp = client.post("/item", json={"name": "Test Item", "price": 100.0})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Item"
    assert data["price"] == 100.0
    assert data["deleted"] is False
    assert isinstance(data["id"], int)

def test_get_item(client):
    post_resp = client.post("/item", json={"name": "Test", "price": 50.0})
    item_id = post_resp.json()["id"]
    resp = client.get(f"/item/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test"

def test_get_nonexistent_item(client):
    resp = client.get("/item/9999")
    assert resp.status_code == 404

def test_list_items(client):
    id1 = client.post("/item", json={"name": "Item1", "price": 10.0}).json()["id"]
    id2 = client.post("/item", json={"name": "Item2", "price": 20.0}).json()["id"]
    resp = client.get("/item")
    returned_ids = set(item["id"] for item in resp.json())
    assert {id1, id2}.issubset(returned_ids)

def test_update_item(client):
    item_id = client.post("/item", json={"name": "Original", "price": 10.0}).json()["id"]
    resp = client.put(f"/item/{item_id}", json={"name": "Updated", "price": 20.0})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"
    assert resp.json()["price"] == 20.0

def test_patch_item(client):
    item_id = client.post("/item", json={"name": "Original", "price": 10.0}).json()["id"]
    resp = client.patch(f"/item/{item_id}", json={"price": 30.0})
    assert resp.status_code == 200
    assert resp.json()["price"] == 30.0

def test_delete_item(client):
    item_id = client.post("/item", json={"name": "ToDelete", "price": 10.0}).json()["id"]
    resp = client.delete(f"/item/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    assert client.get(f"/item/{item_id}").status_code == 404

def test_create_cart(client):
    resp = client.post("/cart")
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data

def test_get_cart(client):
    cart_id = client.post("/cart").json()["id"]
    resp = client.get(f"/cart/{cart_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cart_id

def test_add_item_to_cart(client):
    item_id = client.post("/item", json={"name": "Test", "price": 10.0}).json()["id"]
    cart_id = client.post("/cart").json()["id"]
    resp = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 1

def test_cart_list_filtering(client):
    id1 = client.post("/item", json={"name": "Item1", "price": 10.0}).json()["id"]
    id2 = client.post("/item", json={"name": "Item2", "price": 20.0}).json()["id"]
    cart_id = client.post("/cart").json()["id"]
    client.post(f"/cart/{cart_id}/add/{id1}")
    client.post(f"/cart/{cart_id}/add/{id1}")
    client.post(f"/cart/{cart_id}/add/{id2}")

    resp = client.get("/cart?min_price=15")
    assert any(cart for cart in resp.json() if cart["price"] >= 15)

def test_get_deleted_item(client):
    item_id = client.post("/item", json={"name": "Test", "price": 10.0}).json()["id"]
    client.delete(f"/item/{item_id}")
    resp = client.get(f"/item/{item_id}")
    assert resp.status_code == 404
    resp2 = client.get("/item?show_deleted=true")
    deleted_ids = [item["id"] for item in resp2.json() if item["deleted"]]
    assert item_id in deleted_ids

def test_patch_nonexistent_item(client):
    resp = client.patch("/item/99999", json={"price": 30.0})
    assert resp.status_code == 404

def test_patch_deleted_item(client):
    item_id = client.post("/item", json={"name": "Test", "price": 10.0}).json()["id"]
    client.delete(f"/item/{item_id}")
    resp = client.patch(f"/item/{item_id}", json={"price": 30.0})
    assert resp.status_code == 304 or resp.status_code == 404
