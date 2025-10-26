import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from shop_api.main import app

client = TestClient(app)


def test_create_cart_and_add_item():
    r_item = client.post("/item", json={"name": "ItemCart", "price": 50})
    item_id = r_item.json()["id"]

    r_cart = client.post("/cart")
    cart_id = r_cart.json()["id"]

    r_add = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert r_add.status_code == 200
    assert r_add.json()["items"][0]["id"] == item_id
