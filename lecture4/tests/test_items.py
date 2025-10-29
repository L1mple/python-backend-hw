from http import HTTPStatus

def test_create_and_get_item(client):
    r = client.post("/item", json={"name": "X", "price": 9.99})
    assert r.status_code == HTTPStatus.CREATED
    iid = r.json()["id"]

    r = client.get(f"/item/{iid}")
    assert r.status_code == 200
    assert r.json()["name"] == "X"
    assert r.json()["price"] == 9.99

def test_list_filters_pagination(client):
    client.post("/item", json={"name": "C", "price": 300})
    r = client.get("/item", params={"min_price": 150, "offset": 0, "limit": 2})
    assert r.status_code == 200
    assert all(i["price"] >= 150 for i in r.json())

def test_put_patch_delete_and_not_modified(client):
    r = client.post("/item", json={"name": "Y", "price": 10})
    iid = r.json()["id"]

    r = client.put(f"/item/{iid}", json={"name": "Y2", "price": 20})
    assert r.status_code == 200
    assert r.json()["name"] == "Y2"

    r = client.patch(f"/item/{iid}", json={"price": 25})
    assert r.status_code == 200
    assert r.json()["price"] == 25.0

    r = client.delete(f"/item/{iid}")
    assert r.status_code == 200 or r.status_code == 204 or r.text == ""

    # повторное изменение удалённого — 304 NOT_MODIFIED согласно ТЗ
    r = client.put(f"/item/{iid}", json={"name": "Z", "price": 5})
    assert r.status_code == HTTPStatus.NOT_MODIFIED

    # get удалённого — 404
    r = client.get(f"/item/{iid}")
    assert r.status_code == HTTPStatus.NOT_FOUND

def test_list_show_deleted_flag(client):
    r = client.post("/item", json={"name": "D", "price": 50}); iid = r.json()["id"]
    client.delete(f"/item/{iid}")
    r = client.get("/item")
    assert all(not it["deleted"] for it in r.json())
    r = client.get("/item", params={"show_deleted": True})
    ids = [it["id"] for it in r.json()]
    assert iid in ids
