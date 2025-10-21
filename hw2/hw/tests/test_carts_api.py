from __future__ import annotations


def _mk_items(client):
    a = client.post("/item", json={"name": "Pen", "price": 10}).json()
    b = client.post("/item", json={"name": "Book", "price": 25}).json()
    c = client.post("/item", json={"name": "Old", "price": 5}).json()
    client.delete(f"/item/{c['id']}")  # недоступный
    return a, b, c


def test_cart_create_add_get(client):
    a, b, c = _mk_items(client)
    cart = client.post("/cart").json()
    cid = cart["id"]

    r = client.post(f"/cart/{cid}/add/{a['id']}")
    assert r.status_code == 200
    assert r.json()["items"][0]["quantity"] == 1
    assert r.json()["price"] == 10

    r = client.post(f"/cart/{cid}/add/{a['id']}")
    assert r.json()["items"][0]["quantity"] == 2
    assert r.json()["price"] == 20

    # добавим книгу
    r = client.post(f"/cart/{cid}/add/{b['id']}")
    assert r.json()["price"] == 45

    # добавим «удалённый» товар — он учитывается в списке, но не в цене
    r = client.post(f"/cart/{cid}/add/{c['id']}")
    data = r.json()
    names = {i["name"] for i in data["items"]}
    assert "Old" in names
    # цена не изменилась
    assert data["price"] == 45

    # ошибка: неизвестная корзина/товар
    r = client.post("/cart/999/add/1")
    assert r.status_code == 404
    r = client.post(f"/cart/{cid}/add/999")
    assert r.status_code == 404


def test_list_carts_filters(client):
    a, b, _ = _mk_items(client)
    c1 = client.post("/cart").json()["id"]
    c2 = client.post("/cart").json()["id"]

    client.post(f"/cart/{c1}/add/{a['id']}")  # цена 10, qty 1
    client.post(f"/cart/{c2}/add/{a['id']}")  # цена 20, qty 2
    client.post(f"/cart/{c2}/add/{a['id']}")
    client.post(f"/cart/{c2}/add/{b['id']}")  # +25 => 45

    # min_price
    r = client.get("/cart", params={"min_price": 20})
    ids = {c["id"] for c in r.json()}
    assert ids == {c2}

    # max_price
    r = client.get("/cart", params={"max_price": 15})
    ids = {c["id"] for c in r.json()}
    assert ids == {c1}

    # min_quantity/max_quantity
    r = client.get("/cart", params={"min_quantity": 3})
    ids = {c["id"] for c in r.json()}
    assert ids == {c2}

    r = client.get("/cart", params={"max_quantity": 1})
    ids = {c["id"] for c in r.json()}
    assert ids == {c1}

    # пагинация
    r = client.get("/cart", params={"offset": 0, "limit": 1})
    assert len(r.json()) == 1
