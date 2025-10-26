import pytest
from fastapi.testclient import TestClient
from shop_api.db import Base, SessionLocal, engine
from shop_api.main import app, get_db

# ------------------------
# Настройка временной БД
# ------------------------
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ------------------------
# Фикстура для чистки БД перед каждым тестом
# ------------------------
@pytest.fixture(autouse=True)
def clean_db():
    db = SessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


# ------------------------
# Helper функции
# ------------------------
def create_item(name="TestItem", price=10.0):
    r = client.post("/item", json={"name": name, "price": price})
    assert r.status_code == 201
    return r.json()["id"]


def create_cart():
    r = client.post("/cart")
    assert r.status_code == 201
    return r.json()["id"]


def add_item_to_cart(cart_id, item_id):
    r = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert r.status_code == 200
    return r.json()


def get_item(item_id):
    r = client.get(f"/item/{item_id}")
    return r


def patch_item(item_id, data):
    r = client.patch(f"/item/{item_id}", json=data)
    return r


def delete_item(item_id):
    r = client.delete(f"/item/{item_id}")
    return r


def get_cart(cart_id):
    r = client.get(f"/cart/{cart_id}")
    return r


# ------------------------
# Тесты Item CRUD
# ------------------------
@pytest.mark.parametrize("name,price", [("Test", 10.0), ("Old", 5.0)])
def test_create_and_get_item(name, price):
    item_id = create_item(name, price)
    r = get_item(item_id)
    assert r.status_code == 200
    assert r.json()["name"] == name
    assert r.json()["price"] == price


def test_get_nonexistent_item():
    r = get_item(999)
    assert r.status_code == 404


def test_replace_item():
    item_id = create_item("Old", 5.0)
    r = client.put(f"/item/{item_id}", json={"name": "New", "price": 15.0})
    assert r.status_code == 200
    assert r.json()["name"] == "New"
    assert r.json()["price"] == 15.0


def test_replace_nonexistent_item():
    r = client.put("/item/999", json={"name": "X", "price": 1.0})
    assert r.status_code == 400


def test_patch_item_name_and_price():
    item_id = create_item("PatchMe", 20.0)
    r = patch_item(item_id, {"name": "Patched"})
    assert r.status_code == 200
    assert r.json()["name"] == "Patched"


def test_patch_item_price_only():
    item_id = create_item("Original", 50.0)
    r = patch_item(item_id, {"price": 123.0})
    assert r.status_code == 200
    assert r.json()["price"] == 123.0
    assert r.json()["name"] == "Original"


def test_patch_nonexistent_item():
    r = patch_item(999, {"name": "NewName", "price": 123.0})
    assert r.status_code == 400
    assert r.json()["detail"] == "Item not found"


def test_patch_deleted_item():
    item_id = create_item("ToDelete", 5.0)
    delete_item(item_id)
    r = patch_item(item_id, {"price": 10.0})
    assert r.status_code == 304


def test_delete_nonexistent_item():
    r = delete_item(999)
    assert r.status_code == 400


# ------------------------
# Тесты Cart CRUD
# ------------------------
def test_create_cart_and_add_item():
    cart_id = create_cart()
    item_id = create_item("ItemCart", 5.0)
    data = add_item_to_cart(cart_id, item_id)
    assert data["items"][0]["id"] == item_id


def test_add_to_nonexistent_cart():
    item_id = create_item("X", 1.0)
    r = client.post(f"/cart/999/add/{item_id}")
    assert r.status_code == 400


def test_add_nonexistent_item_to_cart():
    cart_id = create_cart()
    r = client.post(f"/cart/{cart_id}/add/999")
    assert r.status_code == 404


def test_add_to_cart_existing_item():
    cart_id = create_cart()
    item_id = create_item("X", 1.0)
    add_item_to_cart(cart_id, item_id)
    data = add_item_to_cart(cart_id, item_id)
    assert data["items"][0]["quantity"] == 2


def test_get_nonexistent_cart():
    r = get_cart(999)
    assert r.status_code == 400
    assert r.json()["detail"] == "Cart not found"


def test_get_existing_cart():
    cart_id = create_cart()
    item_id = create_item("Item1", 10.0)
    add_item_to_cart(cart_id, item_id)
    r = get_cart(cart_id)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == cart_id
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == item_id
    assert data["price"] == 10.0


# ------------------------
# Тесты фильтров Item и Cart
# ------------------------
def test_list_items_filters():
    create_item("A", 1.0)
    create_item("B", 10.0)
    r = client.get("/item?min_price=5")
    assert all(i["price"] >= 5 for i in r.json())


def test_list_items_min_max_price():
    create_item("Cheap", 1.0)
    create_item("Expensive", 100.0)
    r = client.get("/item?min_price=50")
    assert all(i["price"] >= 50 for i in r.json())
    r = client.get("/item?max_price=10")
    assert all(i["price"] <= 10 for i in r.json())


def test_list_carts_filters():
    cart_id = create_cart()
    item_id = create_item("Item", 10.0)
    add_item_to_cart(cart_id, item_id)
    r = client.get("/cart?min_price=5")
    assert all(c["price"] >= 5 for c in r.json())


def test_list_carts_price_quantity_filters():
    cart_id = create_cart()
    item_id = create_item("Item", 10.0)
    add_item_to_cart(cart_id, item_id)

    # price filter
    assert client.get("/cart?min_price=20").json() == []
    assert client.get("/cart?max_price=5").json() == []

    # quantity filter
    assert client.get("/cart?min_quantity=10").json() == []
    assert client.get("/cart?max_quantity=0").json() == []


# ------------------------
# Тест закрытия БД
# ------------------------
def test_get_db_close_called():
    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    try:
        next(db_gen)
    except StopIteration:
        pass
