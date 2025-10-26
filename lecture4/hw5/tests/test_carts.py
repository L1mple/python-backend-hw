def _id(r):
    b = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
    return b.get("id") or b.get("cart_id") or int(r.headers.get("Location", "0").split("/")[-1])

def test_cart_flow(client):
    r = client.post("/cart")
    assert r.status_code in (200, 201)
    cart_id = _id(r)
    r = client.post("/item", json={"name": "D", "price": 7})
    item_id = (r.json().get("id") or r.json().get("item_id"))
    r = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert r.status_code in (200, 201, 204)
    r = client.get(f"/cart/{cart_id}")
    assert r.status_code == 200
    j = r.json()
    total = float(j.get("total_price", 0))
    assert total >= 7.0

def test_cart_filters(client):
    for i in range(3):
        r = client.post("/cart")
        cart_id = _id(r)
        item = client.post("/item", json={"name": f"E{i}", "price": 5 + i}).json()
        for _ in range(i + 1):
            client.post(f"/cart/{cart_id}/add/{item.get('id') or item.get('item_id')}")
    r = client.get("/cart?min_price=5&max_price=20&min_quantity=1")
    assert r.status_code == 200
    assert isinstance(r.json(), list)