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


def test_get_item_fail(client):
    res = client.get("/item/1")
    assert res.status_code == 404


def test_get_item_list(client):
    for i in range(1, 4):
        res = client.post("/item", json={"name": f"item{i}", "price": float(i)})
        assert res.status_code == 201

    res_delete = client.delete("/item/2")
    assert res_delete.status_code == 200

    res_list = client.get("/item")
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) == 2
    assert all(item["id"] != 2 for item in items)

    res_all = client.get("/item?show_deleted=true")
    assert res_all.status_code == 200
    all_items = res_all.json()
    assert len(all_items) == 3
    assert any(item["id"] == 2 for item in all_items)

    res_min = client.get("/item?min_price=2.0")
    assert res_min.status_code == 200
    min_items = res_min.json()
    assert len(min_items) == 1
    assert all(item["price"] >= 2.0 for item in min_items)

    res_max = client.get("/item?max_price=2.0")
    assert res_max.status_code == 200
    max_items = res_max.json()
    assert len(max_items) == 1
    assert all(item["price"] <= 2.0 for item in max_items)

    res_range = client.get("/item?min_price=1.0&max_price=2.0")
    assert res_range.status_code == 200
    range_items = res_range.json()
    assert len(range_items) == 1
    assert all(1.0 <= item["price"] <= 2.0 for item in range_items)


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


def test_put_item_fail(client):
    res_create = client.post("/item", json={"name": "item1", "price": 1.0})
    item_id = res_create.json()["id"]
    assert res_create.status_code == 201

    next_id = item_id + 1
    res_put = client.put(f"/item/{next_id}", json={"name": "item2", "price": 2.0})
    assert res_put.status_code == 404


def test_patch_item(client):
    client.post("/item", json={"name": "item1", "price": 1.0})
    res = client.patch(f"/item/1", json={"price": 2.0})
    assert res.status_code == 200
    assert res.json()["price"] == 2.0


def test_patch_item_fail(client):
    client.post("/item", json={"name": "item1", "price": 1.0})
    res = client.patch(f"/item/2", json={"price": 2.0})
    assert res.status_code == 404

    client.delete(f"/item/1")
    res = client.patch(f"/item/1", json={"price": 2.0})
    assert res.status_code == 304


def test_delete_item(client):
    client.post("/item", json={"name": "item1", "price": 1.0})
    res = client.delete(f"/item/1")
    assert res.status_code == 200
    res2 = client.get(f"/item/1")
    assert res2.status_code == 404
