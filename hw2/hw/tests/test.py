from http import HTTPStatus
from fastapi.testclient import TestClient
from shop_api.main import app

client = TestClient(app)


def test_get_item_not_found():
    """Проверяет 404 при запросе несуществующего товара"""
    resp = client.get("/item/999999")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_get_cart_not_found():
    """Проверяет 404 при запросе несуществующей корзины"""
    resp = client.get("/cart/999999")
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_add_deleted_item_to_cart_returns_400():
    """Проверяет 400 при добавлении удалённого товара в корзину"""
    # создаём корзину
    cart_id = client.post("/cart").json()["id"]
    # создаём и удаляем товар
    item_id = client.post("/item", json={"name": "X", "price": 1.0}).json()["id"]
    client.delete(f"/item/{item_id}")
    # пытаемся добавить удалённый товар
    resp = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert resp.status_code == HTTPStatus.BAD_REQUEST
