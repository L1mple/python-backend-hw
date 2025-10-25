from __future__ import annotations

def test_get_cart_not_found(client):
    r = client.get("/cart/99999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Cart not found"


def test_put_item_not_found(client):
    r = client.put("/item/99999", json={"name": "Z", "price": 1})
    assert r.status_code == 404
    assert r.json()["detail"] == "Item not found"
