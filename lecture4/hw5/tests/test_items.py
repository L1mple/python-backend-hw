def _id(r):
    b = r.json()
    return b.get("id") or b.get("item_id") or int(r.headers.get("Location", "0").split("/")[-1])

def test_create_and_get_item(client):
    r = client.post("/item", json={"name": "A", "price": 10})
    assert r.status_code in (200, 201)
    item_id = _id(r)
    r = client.get(f"/item/{item_id}")
    assert r.status_code == 200
    j = r.json()
    assert j.get("name") == "A"
    assert float(j.get("price", 0)) == 10.0

def test_list_filter_pagination(client):
    for i in range(1, 6):
        client.post("/item", json={"name": f"I{i}", "price": i * 5})
    r = client.get("/item?min_price=10&max_price=20&offset=0&limit=10")
    assert r.status_code == 200
    lst = r.json()
    assert all(10 <= float(x.get("price", 0)) <= 20 for x in lst)

def test_update_and_patch_item(client):
    r = client.post("/item", json={"name": "B", "price": 1})
    item_id = _id(r)
    r = client.put(f"/item/{item_id}", json={"name": "B2", "price": 2})
    assert r.status_code in (200, 204)
    r = client.patch(f"/item/{item_id}", json={"price": 3})
    assert r.status_code in (200, 204)
    r = client.get(f"/item/{item_id}")
    assert r.json().get("name") in ("B2", "B")
    assert float(r.json().get("price", 0)) == 3.0

def test_soft_delete_and_show_deleted(client):
    r = client.post("/item", json={"name": "C", "price": 9})
    item_id = _id(r)
    r = client.delete(f"/item/{item_id}")
    assert r.status_code in (200, 204)
    r = client.get("/item")
    assert all(x.get("id") != item_id and x.get("item_id") != item_id for x in r.json())
    r = client.get("/item?show_deleted=1")
    assert any((x.get("id") == item_id) or (x.get("item_id") == item_id) for x in r.json())

def test_not_found_item(client):
    r = client.get("/item/999999")
    assert r.status_code in (404, 422)