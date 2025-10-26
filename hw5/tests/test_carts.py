def test_create_cart(client):
    res = client.post("/cart")
    assert res.status_code == 201
    assert res.json()["id"] == 1