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


def test_get_item_list(client):
    for i in range(1, 4):
        res = client.post("/item", json={"name": f"item{i}", "price": float(i)})
        assert res.status_code == 201

    res_list = client.get("/item")
    assert res_list.status_code == 200
    items = res_list.json()
    for i in range(1, 4):
        assert any(item["name"] == f"item{i}" and item["price"] == float(i) for item in items)


def test_put_item(client):
    res_create = client.post("/item", json={"name": "item1", "price": 1.0})
    item_id = res_create.json()["id"]
    assert res_create.status_code == 201

    res_put = client.put(f"/item/{item_id}", json={"name": "item2", "price": 2.0})
    assert res_put.status_code == 200
    item = res_put.json()
    assert item["id"] == item_id
    assert item["name"] == "item2"
    assert item["price"] == 2.0

    res_get = client.get(f"/item/{item_id}")
    assert res_get.status_code == 200
    item_get = res_get.json()
    assert item_get["name"] == "item2"
    assert item_get["price"] == 2.0


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
