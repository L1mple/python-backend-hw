def test_create_item(client):
    res = client.post("/item", json={"name": "item1", "price": 1.0})
    assert res.status_code == 201
    body = res.json()
    assert body["id"] == 1
    assert body["name"] == "item1"
    assert body["price"] == 1.0


def test_get_item(client):
    client.post("/item", json={"name": "item1", "price": 1.0})
    res = client.get("/item/1")
    assert res.status_code == 200
    assert res.json()["name"] == "item1"


def test_patch_item(client):
    client.post("/item", json={"name": "item1", "price": 1.0})
    res = client.patch("/item/1", json={"price": 2.0})
    assert res.status_code == 200
    assert res.json()["price"] == 2.0


def test_delete_item(client):
    client.post("/item", json={"name": "item1", "price": 1.0})
    res = client.delete("/item/1")
    assert res.status_code == 200
    res2 = client.get("/item/1")
    assert res2.status_code == 404
