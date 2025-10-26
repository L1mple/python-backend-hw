from http import HTTPStatus
import pytest
from fastapi.testclient import TestClient
from faker import Faker

from shop_api.main import app

client = TestClient(app)
faker = Faker()

@pytest.fixture(scope="session")
def create_item() -> int:
    def _create(name: str = None, price: float = None):
        body = {
            "name": name or f"Товар {faker.word()}",
            "price": price or faker.pyfloat(min_value=5.0, max_value=200.0),
        }
        return client.post("/item", json=body).json()
    return _create


@pytest.fixture(scope="session")
def create_cart() -> int:
    def _create():
        return client.post("/cart").json()
    return _create


def test_create_and_get_item(create_item):
    item = create_item("Test Book", 100)
    res = client.get(f"/item/{item['id']}")
    assert res.status_code == HTTPStatus.OK
    data = res.json()
    assert data["name"] == "Test Book"
    assert data["price"] == 100


def test_get_item_not_found():
    res = client.get("/item/999999")
    assert res.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(
    "query",
    [
        {"min_price": 0},
        {"max_price": 9999},
        {"offset": 0, "limit": 5},
    ],
)
def test_list_items_with_filters(create_item, query):
    create_item("Cheap", 10)
    create_item("Expensive", 500)
    res = client.get("/item", params=query)
    assert res.status_code == HTTPStatus.OK
    assert isinstance(res.json(), list)


def test_update_and_patch_item(create_item):
    item = create_item("Pen", 20)
    put = client.put(f"/item/{item['id']}", json={"name": "Marker", "price": 30})
    assert put.status_code == HTTPStatus.OK
    assert put.json()["name"] == "Marker"

    patch = client.patch(f"/item/{item['id']}", json={"price": 35})
    assert patch.status_code == HTTPStatus.OK
    assert patch.json()["price"] == 35


def test_delete_item(create_item):
    item = create_item("Temp", 15)
    res = client.delete(f"/item/{item['id']}")
    assert res.status_code == HTTPStatus.OK
    res2 = client.get(f"/item/{item['id']}")
    assert res2.status_code == HTTPStatus.NOT_FOUND


def test_update_delete_nonexistent_item():
    for method in ("put", "patch", "delete"):
        func = getattr(client, method)
        kwargs = {"json": {"name": "X", "price": 10}} if method != "delete" else {}
        res = func("/item/99999", **kwargs)
        assert res.status_code == HTTPStatus.NOT_FOUND


def test_create_cart(create_cart):
    res = client.post("/cart")
    assert res.status_code == HTTPStatus.CREATED
    assert "id" in res.json()


def test_add_item_to_cart(create_cart, create_item):
    cart = create_cart()
    item = create_item("Milk", 5)
    res = client.post(f"/cart/{cart['id']}/add/{item['id']}")
    assert res.status_code == HTTPStatus.OK
    assert res.json()["status"] == "ok"


def test_add_nonexistent_item_to_cart(create_cart):
    cart = create_cart()
    res = client.post(f"/cart/{cart['id']}/add/999999")
    assert res.status_code == HTTPStatus.NOT_FOUND


def test_add_item_to_nonexistent_cart(create_item):
    item = create_item("Ghost", 10)
    res = client.post(f"/cart/999999/add/{item['id']}")
    assert res.status_code == HTTPStatus.NOT_FOUND


def test_get_cart(create_cart, create_item):
    cart = create_cart()
    item = create_item("Bread", 10)
    client.post(f"/cart/{cart['id']}/add/{item['id']}")
    res = client.get(f"/cart/{cart['id']}")
    assert res.status_code == HTTPStatus.OK
    data = res.json()
    assert isinstance(data["items"], list)
    assert data["price"] >= 10


def test_get_cart_not_found():
    res = client.get("/cart/999999")
    assert res.status_code == HTTPStatus.NOT_FOUND


def test_list_carts_basic(create_cart):
    create_cart()
    res = client.get("/cart")
    assert res.status_code == HTTPStatus.OK
    assert isinstance(res.json(), list)


@pytest.mark.parametrize(
    "query",
    [
        {"min_price": 0},
        {"max_price": 9999},
        {"min_quantity": 0},
        {"max_quantity": 999},
    ],
)
def test_list_carts_with_filters(create_cart, create_item, query):
    item = create_item("ItemX", 50)
    cart = create_cart()
    client.post(f"/cart/{cart['id']}/add/{item['id']}")
    res = client.get("/cart", params=query)
    assert res.status_code == HTTPStatus.OK
    assert isinstance(res.json(), list)


def test_cart_with_deleted_item(create_cart, create_item):
    item = create_item("Deleted", 5)
    cart = create_cart()
    client.post(f"/cart/{cart['id']}/add/{item['id']}")
    client.delete(f"/item/{item['id']}")

    res = client.get(f"/cart/{cart['id']}")
    assert res.status_code == HTTPStatus.OK
    data = res.json()
    assert any(not i["available"] for i in data["items"])