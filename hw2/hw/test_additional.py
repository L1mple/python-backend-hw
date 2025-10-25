import pytest
from fastapi.testclient import TestClient
from shop_api.main import app, _make_username, _get_item, _build_cart_view
from shop_api.database import get_session
from fastapi import HTTPException

client = TestClient(app)


def test_websocket_basic():
    with client.websocket_connect("/chat/room") as ws1:
        with client.websocket_connect("/chat/room") as ws2:
            ws1.send_text("hello")
            assert "hello" in ws2.receive_text()


def test_cart_add_increment_quantity():
    item = client.post("/item", json={"name": "T", "price": 100}).json()
    cart = client.post("/cart").json()
    client.post(f"/cart/{cart['id']}/add/{item['id']}")
    response = client.post(f"/cart/{cart['id']}/add/{item['id']}")
    assert response.json()['items'][0]['quantity'] == 2


def test_item_patch_separate_fields():
    item = client.post("/item", json={"name": "Old", "price": 50}).json()
    assert client.patch(f"/item/{item['id']}", json={"name": "New"}).json()['name'] == "New"
    
    item2 = client.post("/item", json={"name": "Test", "price": 50}).json()
    assert client.patch(f"/item/{item2['id']}", json={"price": 100}).json()['price'] == 100


def test_item_patch_validations():
    item = client.post("/item", json={"name": "T", "price": 50}).json()
    assert client.patch(f"/item/{item['id']}", json={"deleted": True}).status_code == 422
    assert client.patch(f"/item/{item['id']}", json={"unknown": "x"}).status_code == 422


def test_item_patch_deleted():
    item = client.post("/item", json={"name": "T", "price": 50}).json()
    client.delete(f"/item/{item['id']}")
    assert client.patch(f"/item/{item['id']}", json={"name": "N"}).status_code == 304


def test_delete_operations():
    item = client.post("/item", json={"name": "T", "price": 50}).json()
    assert client.delete(f"/item/{item['id']}").status_code == 200
    assert client.delete(f"/item/{item['id']}").status_code == 200
    assert client.delete("/item/999999").status_code == 200


def test_cart_with_deleted_item():
    item = client.post("/item", json={"name": "T", "price": 100}).json()
    cart = client.post("/cart").json()
    client.post(f"/cart/{cart['id']}/add/{item['id']}")
    client.delete(f"/item/{item['id']}")
    data = client.get(f"/cart/{cart['id']}").json()
    assert data['items'][0]['available'] == False
    assert data['price'] == 0


def test_item_filters():
    client.post("/item", json={"name": "Cheap", "price": 10})
    client.post("/item", json={"name": "Expensive", "price": 500})
    items = client.get("/item?min_price=100&max_price=600&limit=100").json()
    assert all(100 <= i['price'] <= 600 for i in items)


def test_item_show_deleted():
    item = client.post("/item", json={"name": "D", "price": 50}).json()
    client.delete(f"/item/{item['id']}")
    items = client.get("/item?show_deleted=true&limit=100").json()
    deleted = [i for i in items if i['id'] == item['id']]
    assert len(deleted) > 0 and deleted[0]['deleted']


def test_cart_filters():
    item = client.post("/item", json={"name": "A", "price": 200}).json()
    cart = client.post("/cart").json()
    for _ in range(3):
        client.post(f"/cart/{cart['id']}/add/{item['id']}")
    
    carts = client.get("/cart?min_price=100&max_price=1000&min_quantity=2&max_quantity=5&limit=100").json()
    assert any(c['id'] == cart['id'] for c in carts)


def test_pagination():
    for i in range(15):
        client.post("/item", json={"name": f"I{i}", "price": i})
    assert len(client.get("/item?offset=10&limit=5").json()) <= 5
    
    for _ in range(12):
        client.post("/cart")
    assert len(client.get("/cart?offset=5&limit=5").json()) <= 5


def test_404_scenarios():
    assert client.get("/item/999999").status_code == 404
    assert client.get("/cart/999999").status_code == 404
    assert client.put("/item/999999", json={"name": "X", "price": 1}).status_code == 404
    assert client.patch("/item/999999", json={"name": "X"}).status_code == 404
    
    item = client.post("/item", json={"name": "T", "price": 1}).json()
    cart = client.post("/cart").json()
    assert client.post(f"/cart/999999/add/{item['id']}").status_code == 404
    assert client.post(f"/cart/{cart['id']}/add/999999").status_code == 404
    
    client.delete(f"/item/{item['id']}")
    assert client.post(f"/cart/{cart['id']}/add/{item['id']}").status_code == 404
    assert client.put(f"/item/{item['id']}", json={"name": "N", "price": 10}).status_code == 404


def test_make_username():
    u1, u2 = _make_username(), _make_username()
    assert u1.startswith("user-") and u1 != u2


@pytest.mark.asyncio
async def test_async_functions():
    item = client.post("/item", json={"name": "T", "price": 10}).json()
    cart = client.post("/cart").json()
    client.post(f"/cart/{cart['id']}/add/{item['id']}")
    client.delete(f"/item/{item['id']}")
    
    async for session in get_session():
        with pytest.raises(HTTPException):
            await _get_item(item['id'], session)
        with pytest.raises(HTTPException):
            await _get_item(999999, session)
        
        view = await _build_cart_view(cart['id'], session)
        assert view.price == 0
        
        with pytest.raises(HTTPException):
            await _build_cart_view(999999, session)
        break


def test_pydantic_validator():
    from shop_api.main import ItemPatch
    assert ItemPatch.forbid_deleted_and_unknown("not_dict") == "not_dict"
