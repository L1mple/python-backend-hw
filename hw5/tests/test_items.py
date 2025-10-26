def test_create_item(client):
    res = client.post("/item", json={"name": "item1", "price": 1.0})
    assert res.status_code == 201
    body = res.json()
    assert body["id"] == 1
    assert body["name"] == "item1"
    assert body["price"] == 1.0
