from http import HTTPStatus


def test_create_item_success(client):
    response = client.post("/item/", json={"name": "Test Item", "price": 10.5})
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()

    assert data["name"] == "Test Item"
    assert data["price"] == 10.5
    assert "id" in data
    assert response.headers["location"] == f"/item/{data['id']}"


def test_get_item_not_found(client):
    response = client.get("/item/999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_item_by_id_success(client):
    create_response = client.post("/item/", json={"name": "Another Item", "price": 99.9})
    item_id = create_response.json()["id"]

    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["id"] == item_id
    assert data["name"] == "Another Item"


def test_get_items_list(client):
    client.post("/item/", json={"name": "Item 1", "price": 10})
    client.post("/item/", json={"name": "Item 2", "price": 20})
    client.post("/item/", json={"name": "Item 3", "price": 30})

    response = client.get("/item/")
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 3

    response = client.get("/item/?min_price=15&max_price=25")
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Item 2"

    response = client.get("/item/?offset=1&limit=1")
    assert len(response.json()) == 1
    assert response.json()[0]["price"] == 20


def test_delete_item(client):
    create_response = client.post("/item/", json={"name": "Deletable Item", "price": 5})
    item_id = create_response.json()["id"]

    delete_response = client.delete(f"/item/{item_id}")
    assert delete_response.status_code == HTTPStatus.OK

    get_response = client.get(f"/item/{item_id}")
    assert get_response.status_code == HTTPStatus.NOT_FOUND

    list_response = client.get("/item/?show_deleted=true")
    assert len(list_response.json()) == 1
    deleted_item = list_response.json()[0]
    assert deleted_item["id"] == item_id
    assert deleted_item["deleted"] is True

    delete_response_2 = client.delete(f"/item/{item_id}")
    assert delete_response_2.status_code == HTTPStatus.OK


def test_update_item_put(client):
    create_response = client.post("/item/", json={"name": "Old Name", "price": 100})
    item_id = create_response.json()["id"]

    response = client.put(f"/item/{item_id}", json={"name": "New Name", "price": 200, "deleted": False})
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["name"] == "New Name"
    assert data["price"] == 200

    response_not_found = client.put("/item/999", json={"name": "New Name", "price": 200, "deleted": False})
    assert response_not_found.status_code == HTTPStatus.NOT_MODIFIED


def test_update_item_patch(client):
    create_response = client.post("/item/", json={"name": "Original", "price": 50})
    item_id = create_response.json()["id"]

    response_name = client.patch(f"/item/{item_id}", json={"name": "Patched Name"})
    assert response_name.status_code == HTTPStatus.OK
    assert response_name.json()["name"] == "Patched Name"
    assert response_name.json()["price"] == 50


    response_price = client.patch(f"/item/{item_id}", json={"price": 75.5})
    assert response_price.status_code == HTTPStatus.OK
    assert response_price.json()["name"] == "Patched Name"
    assert response_price.json()["price"] == 75.5

    response_not_found = client.patch("/item/999", json={"name": "New Name"})
    assert response_not_found.status_code == HTTPStatus.NOT_MODIFIED


def test_create_cart_success(client):
    response = client.post("/cart/")
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["items"] == []
    assert data["price"] == 0.0
    assert "id" in data
    assert response.headers["location"] == f"/cart/{data['id']}"


def test_get_cart_not_found(client):
    response = client.get("/cart/999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_item_to_cart(client):
    item_resp = client.post("/item/", json={"name": "Burger", "price": 10})
    item_id = item_resp.json()["id"]
    cart_resp = client.post("/cart/")
    cart_id = cart_resp.json()["id"]

    add_resp = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert add_resp.status_code == HTTPStatus.CREATED
    cart_data = add_resp.json()
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["id"] == item_id
    assert cart_data["items"][0]["quantity"] == 1
    assert cart_data["price"] == 10.0

    add_resp_2 = client.post(f"/cart/{cart_id}/add/{item_id}")
    cart_data_2 = add_resp_2.json()
    assert len(cart_data_2["items"]) == 1
    assert cart_data_2["items"][0]["quantity"] == 2
    assert cart_data_2["price"] == 20.0

    add_resp_no_cart = client.post(f"/cart/999/add/{item_id}")
    assert add_resp_no_cart.status_code != HTTPStatus.OK


def test_get_cart_by_id(client):
    cart_resp = client.post("/cart/")
    cart_id = cart_resp.json()["id"]

    get_resp = client.get(f"/cart/{cart_id}")
    assert get_resp.status_code == HTTPStatus.OK
    assert get_resp.json()["id"] == cart_id


def test_interaction_delete_item_from_cart(client):
    item_resp = client.post("/item/", json={"name": "Fries", "price": 5})
    item_id = item_resp.json()["id"]
    cart_resp = client.post("/cart/")
    cart_id = cart_resp.json()["id"]
    client.post(f"/cart/{cart_id}/add/{item_id}")

    client.delete(f"/item/{item_id}")

    cart_get_resp = client.get(f"/cart/{cart_id}")
    cart_data = cart_get_resp.json()
    assert cart_data["price"] == 0.0
    assert cart_data["items"][0]["available"] is False


def test_interaction_update_item_in_cart(client):
    item_resp = client.post("/item/", json={"name": "Item 1", "price": 2})
    item_id = item_resp.json()["id"]
    cart_resp = client.post("/cart/")
    cart_id = cart_resp.json()["id"]
    client.post(f"/cart/{cart_id}/add/{item_id}")
    client.post(f"/cart/{cart_id}/add/{item_id}")

    client.put(f"/item/{item_id}", json={"name": "Item 2", "price": 3, "deleted": False})
    cart_get_resp = client.get(f"/cart/{cart_id}")
    cart_data = cart_get_resp.json()
    assert cart_data["price"] == 6.0
    assert cart_data["items"][0]["name"] == "New Soda"

    client.patch(f"/item/{item_id}", json={"price": 2.5})
    cart_get_resp_2 = client.get(f"/cart/{cart_id}")
    cart_data_2 = cart_get_resp_2.json()
    assert cart_data_2["price"] == 5.0


def test_get_carts_list(client):
    item1_resp = client.post("/item/", json={"name": "A", "price": 10})
    item1_id = item1_resp.json()["id"]
    item2_resp = client.post("/item/", json={"name": "B", "price": 50})
    item2_id = item2_resp.json()["id"]

    cart1_resp = client.post("/cart/")
    cart1_id = cart1_resp.json()["id"]
    client.post(f"/cart/{cart1_id}/add/{item1_id}")
    client.post(f"/cart/{cart1_id}/add/{item1_id}")
    client.post(f"/cart/{cart1_id}/add/{item1_id}")

    cart2_resp = client.post("/cart/")
    cart2_id = cart2_resp.json()["id"]
    client.post(f"/cart/{cart2_id}/add/{item1_id}")
    client.post(f"/cart/{cart2_id}/add/{item2_id}")

    resp_price = client.get("/cart/?min_price=50")
    assert len(resp_price.json()) == 1
    assert resp_price.json()[0]["id"] == cart2_id

    resp_quant = client.get("/cart/?min_quantity=3")
    assert len(resp_quant.json()) == 1
    assert resp_quant.json()[0]["id"] == cart1_id
