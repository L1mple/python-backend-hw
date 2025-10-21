from __future__ import annotations


def test_create_and_get_item(client):
    r = client.post("/item", json={"name": "Pen", "price": 10.5})
    assert r.status_code == 201
    created = r.json()
    assert created["name"] == "Pen"
    assert created["price"] == 10.5
    assert created["deleted"] is False
    assert "Location" in r.headers

    item_id = created["id"]
    r2 = client.get(f"/item/{item_id}")
    assert r2.status_code == 200
    assert r2.json() == created


def test_put_and_delete_item(client):
    item = client.post("/item", json={"name": "A", "price": 1}).json()
    iid = item["id"]

    r = client.put(f"/item/{iid}", json={"name": "B", "price": 2.5})
    assert r.status_code == 200
    assert r.json()["name"] == "B"
    assert r.json()["price"] == 2.5

    r = client.delete(f"/item/{iid}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True

    r = client.get(f"/item/{iid}")
    assert r.status_code == 404  # удалённые не отдаются


def test_list_items_pagination_and_deleted(client):
    for i in range(5):
        client.post("/item", json={"name": f"I{i}", "price": i})
    # пометим один как удалённый
    client.delete("/item/3")

    r = client.get("/item")
    data = r.json()
    assert all(not it["deleted"] for it in data)
    assert len(data) == 4  # один скрыт

    # показать удалённые
    r2 = client.get("/item", params={"show_deleted": True, "limit": 10})
    ids = [it["id"] for it in r2.json()]
    assert 3 in ids

    # пагинация
    r3 = client.get("/item", params={"offset": 2, "limit": 2})
    assert len(r3.json()) == 2
