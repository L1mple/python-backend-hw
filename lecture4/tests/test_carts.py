def test_cart_create_get_add_and_price(client):
    # есть базовые items A=100, B=200
    r = client.post("/cart")
    assert r.status_code == 201
    cid = r.json()["id"]

    r = client.get(f"/cart/{cid}"); assert r.status_code == 200
    assert r.json()["price"] == 0.0

    client.post(f"/cart/{cid}/add/1")  # A
    client.post(f"/cart/{cid}/add/2")  # B
    client.post(f"/cart/{cid}/add/1")  # A again

    r = client.get(f"/cart/{cid}")
    assert r.status_code == 200
    assert r.json()["price"] == 100.0*2 + 200.0*1
    items = {i["id"]: i["quantity"] for i in r.json()["items"]}
    assert items[1] == 2 and items[2] == 1

def test_cart_list_filters_and_quantity_budget(client):
    c1 = client.post("/cart").json()["id"]
    c2 = client.post("/cart").json()["id"]
    client.post(f"/cart/{c1}/add/1"); client.post(f"/cart/{c1}/add/1")
    client.post(f"/cart/{c2}/add/2")

    # price filter
    r = client.get("/cart", params={"min_price": 150})
    assert all(x["price"] >= 150 for x in r.json())

    # quantity budget (min_quantity/max_quantity semantics из ДЗ)
    r = client.get("/cart", params={"max_quantity": 2})
    total_qty = sum(sum(i["quantity"] for i in x["items"]) for x in r.json())
    assert total_qty <= 2
