from __future__ import annotations


def test_patch_only_name_and_price(client):
    it = client.post("/item", json={"name": "X", "price": 10}).json()
    iid = it["id"]

    r = client.patch(f"/item/{iid}", json={"name": "Y"})
    assert r.status_code == 200
    assert r.json()["name"] == "Y"

    r = client.patch(f"/item/{iid}", json={"price": 12.5})
    assert r.status_code == 200
    assert r.json()["price"] == 12.5


def test_patch_forbidden_and_deleted(client):
    it = client.post("/item", json={"name": "X", "price": 10}).json()
    iid = it["id"]

    # запрет поля deleted
    r = client.patch(f"/item/{iid}", json={"deleted": True})
    assert r.status_code == 422

    # лишнее поле
    r = client.patch(f"/item/{iid}", json={"foo": "bar"})
    assert r.status_code == 422

    # пометим удалённым и попробуем патч
    client.delete(f"/item/{iid}")
    r = client.patch(f"/item/{iid}", json={"name": "Z"})
    assert r.status_code == 304

    # по несуществующему id
    r = client.patch("/item/9999", json={"name": "Nope"})
    assert r.status_code == 404
