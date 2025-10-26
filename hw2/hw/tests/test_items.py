from fastapi.testclient import TestClient
from shop_api.main import app

client = TestClient(app)


def test_create_item():
    response = client.post("/item", json={"name": "TestItem", "price": 123.45})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "TestItem"
    assert data["price"] == 123.45
    assert "id" in data


def test_get_item_not_found():
    response = client.get("/item/9999")
    assert response.status_code == 404
