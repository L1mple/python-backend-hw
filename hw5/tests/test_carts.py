from shop_api.src.main import calculate_cart_price
from shop_api.src.models import Cart, CartItem, Item


def test_create_cart(client):
    response = client.post("/cart")
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    cart_id = data["id"]

    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    cart_data = response.json()
    assert cart_data["id"] == cart_id
    assert cart_data["items"] == []
    assert cart_data["price"] == 0.0


def test_get_cart(client):
    response = client.post("/cart")
    cart_id = response.json()["id"]

    response = client.post("/item", json={"name": "Cart Item", "price": 10.0})
    item_id = response.json()["id"]

    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 200

    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    cart_data = response.json()
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["id"] == item_id
    assert cart_data["items"][0]["name"] == "Cart Item"
    assert cart_data["items"][0]["quantity"] == 1
    assert cart_data["price"] == 10.0


def test_get_nonexistent_cart(client):
    response = client.get("/cart/999999")
    assert response.status_code == 404


def test_get_carts(client):
    response = client.post("/cart")
    cart1_id = response.json()["id"]

    response = client.post("/cart")

    response = client.post("/item", json={"name": "Multi Cart Item", "price": 10.0})
    item_id = response.json()["id"]

    client.post(f"/cart/{cart1_id}/add/{item_id}")

    response = client.get("/cart")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_get_carts_with_filters(client):
    response = client.post("/cart")
    cart1_id = response.json()["id"]

    response = client.post("/cart")
    cart2_id = response.json()["id"]

    response = client.post("/item", json={"name": "Cheap Item", "price": 5.0})
    cheap_item_id = response.json()["id"]

    response = client.post("/item", json={"name": "Expensive Item", "price": 20.0})
    expensive_item_id = response.json()["id"]

    client.post(f"/cart/{cart1_id}/add/{cheap_item_id}")
    client.post(f"/cart/{cart2_id}/add/{expensive_item_id}")

    response = client.get("/cart?min_price=10")
    assert response.status_code == 200
    data = response.json()
    cart_ids = [cart["id"] for cart in data]
    assert cart2_id in cart_ids
    assert cart1_id not in cart_ids


def test_add_to_cart(client):
    response = client.post("/cart")
    cart_id = response.json()["id"]

    response = client.post("/item", json={"name": "Add Test", "price": 10.0})
    item_id = response.json()["id"]

    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Item added to cart"

    response = client.get(f"/cart/{cart_id}")
    cart_data = response.json()
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["id"] == item_id


def test_add_existing_item_to_cart(client):
    response = client.post("/cart")
    cart_id = response.json()["id"]

    response = client.post("/item", json={"name": "Duplicate Item", "price": 10.0})
    item_id = response.json()["id"]

    client.post(f"/cart/{cart_id}/add/{item_id}")
    client.post(f"/cart/{cart_id}/add/{item_id}")

    response = client.get(f"/cart/{cart_id}")
    cart_data = response.json()
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["quantity"] == 2


def test_add_nonexistent_item_to_cart(client):
    response = client.post("/cart")
    cart_id = response.json()["id"]

    response = client.post(f"/cart/{cart_id}/add/999999")
    assert response.status_code == 404


def test_add_item_to_nonexistent_cart(client):
    response = client.post("/item", json={"name": "Test Item", "price": 10.0})
    item_id = response.json()["id"]

    response = client.post(f"/cart/999999/add/{item_id}")
    assert response.status_code == 404


def test_add_deleted_item_to_cart(client):
    response = client.post("/cart")
    cart_id = response.json()["id"]

    response = client.post("/item", json={"name": "To Delete", "price": 10.0})
    item_id = response.json()["id"]

    client.delete(f"/item/{item_id}")

    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 400


def test_validation_errors_carts(client):
    # Для корзин
    response = client.get("/cart?offset=-1")
    assert response.status_code == 422

    response = client.get("/cart?limit=0")
    assert response.status_code == 422

    response = client.get("/cart?min_price=-1")
    assert response.status_code == 422

    response = client.get("/cart?max_price=-1")
    assert response.status_code == 422

    response = client.get("/cart?min_quantity=-1")
    assert response.status_code == 422

    response = client.get("/cart?max_quantity=-1")
    assert response.status_code == 422


def test_get_carts_with_quantity_filters(client, db_session):
    response = client.post("/cart")
    cart_id = response.json()["id"]

    response = client.post("/item", json={"name": "Quant Item", "price": 10.0})
    item_id = response.json()["id"]

    client.post(f"/cart/{cart_id}/add/{item_id}")

    response = client.get("/cart?min_quantity=1")
    assert response.status_code == 200

    response = client.get("/cart?max_quantity=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


def test_calculate_cart_price(db_session):
    cart = Cart()
    db_session.add(cart)
    db_session.commit()

    item1 = Item(name="Item1", price=10.0)
    item2 = Item(name="Item2", price=20.0, deleted=True)
    db_session.add(item1)
    db_session.add(item2)
    db_session.commit()

    cart_item1 = CartItem(cart_id=cart.id, item_id=item1.id, quantity=2)
    cart_item2 = CartItem(cart_id=cart.id, item_id=item2.id, quantity=1)
    db_session.add(cart_item1)
    db_session.add(cart_item2)
    db_session.commit()

    price = calculate_cart_price(db_session, cart)
    assert price == 20.0


def test_add_to_cart_increment_multiple_times(client):
    """Тест многократного добавления товара"""
    response = client.post("/cart")
    cart_id = response.json()["id"]

    response = client.post("/item", json={"name": "Multi Add", "price": 5.0})
    item_id = response.json()["id"]

    for _ in range(5):
        response = client.post(f"/cart/{cart_id}/add/{item_id}")
        assert response.status_code == 200

    response = client.get(f"/cart/{cart_id}")
    cart_data = response.json()
    assert cart_data["items"][0]["quantity"] == 5
    assert cart_data["price"] == 25.0


def test_get_carts_empty_database(client):
    response = client.get("/cart")
    assert response.status_code == 200
    assert response.json() == []


def test_get_carts_with_both_price_filters(client):
    response = client.post("/cart")
    cart_id = response.json()["id"]

    response = client.post("/item", json={"name": "Mid Price", "price": 15.0})
    item_id = response.json()["id"]

    client.post(f"/cart/{cart_id}/add/{item_id}")

    response = client.get("/cart?min_price=10&max_price=20")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

    response = client.get("/cart?min_price=20&max_price=30")
    assert response.status_code == 200
    data = response.json()
    assert cart_id not in [cart["id"] for cart in data]
