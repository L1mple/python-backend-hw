def test_create_cart(client):
    res = client.post("/cart")
    assert res.status_code == 201
    assert res.json()["id"] == 1


def test_get_cart(client):
    res_cart = client.post("/cart")
    cart_id = res_cart.json()["id"]
    assert res_cart.status_code == 201

    res_item = client.post("/item", json={"name": "item1", "price": 1.0})
    item_id = res_item.json()["id"]
    assert res_item.status_code == 201

    res_add = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert res_add.status_code == 200

    res_get = client.get(f"/cart/{cart_id}")
    assert res_get.status_code == 200
    cart = res_get.json()
    assert cart["id"] == cart_id
    assert cart["price"] == 1.0
    assert len(cart["items"]) == 1
    assert cart["items"][0]["name"] == "item1"
    assert cart["items"][0]["quantity"] == 1


def test_get_cart_fail(client):
    res_get = client.get(f"/cart/{1}")
    assert res_get.status_code == 404


def test_get_cart_list(client):
    res_item = client.post("/item", json={"name": "item1", "price": 1.0})
    item_id = res_item.json()["id"]

    res_cart = client.post("/cart")
    cart_id = res_cart.json()["id"]
    client.post(f"/cart/{cart_id}/add/{item_id}")

    res = client.get("/cart?min_price=0.5&max_price=2.0")
    assert res.status_code == 200
    carts = res.json()
    assert len(carts) >= 1
    assert carts[0]["id"] == cart_id

    res = client.get("/cart?min_price=0.5")
    assert res.status_code == 200
    carts = res.json()
    assert len(carts) >= 1
    assert carts[0]["id"] == cart_id

    res = client.get("/cart?max_price=2.0")
    assert res.status_code == 200
    carts = res.json()
    assert len(carts) >= 1
    assert carts[0]["id"] == cart_id


def test_add_to_cart(client):
    res_item = client.post("/item", json={"name": "item1", "price": 1.0})
    assert res_item.status_code == 201
    item_id = res_item.json()["id"]

    res_cart = client.post("/cart")
    assert res_cart.status_code == 201
    cart_id = res_cart.json()["id"]

    res = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert res.status_code == 200

    res_cart = client.get(f"/cart/{cart_id}")
    assert res_cart.status_code == 200
    cart = res_cart.json()

    assert cart["id"] == cart_id
    assert len(cart["items"]) == 1
    assert cart["items"][0]["name"] == "item1"
    assert cart["items"][0]["quantity"] == 1
    assert cart["price"] == 1.0


def test_add_to_cart_fail(client):
    res_item = client.post("/item", json={"name": "item1", "price": 1.0})
    assert res_item.status_code == 201
    item_id = res_item.json()["id"]

    res_cart = client.post("/cart")
    assert res_cart.status_code == 201
    cart_id = res_cart.json()["id"]

    res = client.post(f"/cart/{cart_id}/add/{item_id + 1}")
    assert res.status_code == 404

    res = client.post(f"/cart/{cart_id + 1}/add/{item_id}")
    assert res.status_code == 404
