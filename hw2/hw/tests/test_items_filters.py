from __future__ import annotations


def _seed(client):
    client.post("/item", json={"name": "Cheap", "price": 1})
    client.post("/item", json={"name": "Mid", "price": 50})
    client.post("/item", json={"name": "High", "price": 100})


def test_price_filters(client):
    _seed(client)

    r = client.get("/item", params={"min_price": 50})
    names = {i["name"] for i in r.json()}
    assert names == {"Mid", "High"}

    r = client.get("/item", params={"max_price": 50})
    names = {i["name"] for i in r.json()}
    assert names == {"Cheap", "Mid"}

    r = client.get("/item", params={"min_price": 0, "max_price": 1})
    names = [i["name"] for i in r.json()]
    assert names == ["Cheap"]
