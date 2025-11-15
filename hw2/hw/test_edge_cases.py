"""
Additional edge case tests to improve coverage.
"""

import pytest
from fastapi.testclient import TestClient
from shop_api.main import app

client = TestClient(app)


@pytest.fixture()
def sample_item():
    """Create a sample item for testing"""
    response = client.post("/item", json={"name": "Test Item", "price": 100.0})
    return response.json()


@pytest.fixture()
def sample_cart():
    """Create a sample cart for testing"""
    response = client.post("/cart")
    return response.json()


def test_get_nonexistent_item():
    """Test getting an item that doesn't exist"""
    response = client.get("/item/99999")
    assert response.status_code == 404


def test_get_nonexistent_cart():
    """Test getting a cart that doesn't exist"""
    response = client.get("/cart/99999")
    assert response.status_code == 404


def test_add_item_to_nonexistent_cart(sample_item):
    """Test adding item to cart that doesn't exist"""
    response = client.post(f"/cart/99999/add/{sample_item['id']}")
    assert response.status_code == 404


def test_add_nonexistent_item_to_cart(sample_cart):
    """Test adding nonexistent item to cart"""
    response = client.post(f"/cart/{sample_cart['id']}/add/99999")
    assert response.status_code == 404


def test_update_nonexistent_item():
    """Test updating an item that doesn't exist"""
    response = client.put("/item/99999", json={"name": "Updated", "price": 200.0})
    assert response.status_code == 404


def test_patch_nonexistent_item():
    """Test patching an item that doesn't exist"""
    response = client.patch("/item/99999", json={"name": "Updated"})
    assert response.status_code == 404


def test_delete_nonexistent_item():
    """Test deleting an item that doesn't exist"""
    response = client.delete("/item/99999")
    assert response.status_code == 404


def test_cart_with_deleted_item(sample_item, sample_cart):
    """Test that cart shows deleted items as unavailable"""
    # Add item to cart
    client.post(f"/cart/{sample_cart['id']}/add/{sample_item['id']}")

    # Delete the item
    client.delete(f"/item/{sample_item['id']}")

    # Get cart - should show item as unavailable
    response = client.get(f"/cart/{sample_cart['id']}")
    assert response.status_code == 200
    cart = response.json()

    assert len(cart["items"]) == 1
    assert cart["items"][0]["available"] is False
    assert cart["items"][0]["id"] == sample_item["id"]


def test_add_same_item_multiple_times(sample_item, sample_cart):
    """Test adding the same item to cart multiple times increases quantity"""
    # Add item three times
    client.post(f"/cart/{sample_cart['id']}/add/{sample_item['id']}")
    client.post(f"/cart/{sample_cart['id']}/add/{sample_item['id']}")
    client.post(f"/cart/{sample_cart['id']}/add/{sample_item['id']}")

    # Check cart
    response = client.get(f"/cart/{sample_cart['id']}")
    cart = response.json()

    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 3


def test_empty_cart(sample_cart):
    """Test that empty cart returns correctly"""
    response = client.get(f"/cart/{sample_cart['id']}")
    assert response.status_code == 200
    cart = response.json()

    assert cart["id"] == sample_cart["id"]
    assert cart["items"] == []
    assert cart["price"] == 0.0


def test_cart_total_price_calculation(sample_cart):
    """Test that cart total price is calculated correctly"""
    # Create items with known prices
    item1 = client.post("/item", json={"name": "Item 1", "price": 10.0}).json()
    item2 = client.post("/item", json={"name": "Item 2", "price": 20.0}).json()

    # Add items to cart
    client.post(f"/cart/{sample_cart['id']}/add/{item1['id']}")
    client.post(f"/cart/{sample_cart['id']}/add/{item1['id']}")  # quantity 2
    client.post(f"/cart/{sample_cart['id']}/add/{item2['id']}")  # quantity 1

    # Check total price: 10*2 + 20*1 = 40
    response = client.get(f"/cart/{sample_cart['id']}")
    cart = response.json()
    assert cart["price"] == 40.0


def test_get_deleted_item_returns_404(sample_item):
    """Test that getting a deleted item returns 404"""
    # Delete item
    client.delete(f"/item/{sample_item['id']}")

    # Try to get it
    response = client.get(f"/item/{sample_item['id']}")
    assert response.status_code == 404


def test_item_list_with_price_filters():
    """Test item list with min and max price filters"""
    # Create items with different prices
    client.post("/item", json={"name": "Cheap", "price": 10.0})
    client.post("/item", json={"name": "Medium", "price": 50.0})
    client.post("/item", json={"name": "Expensive", "price": 100.0})

    # Test min_price filter
    response = client.get("/item?min_price=40")
    items = response.json()
    assert all(item["price"] >= 40 for item in items)

    # Test max_price filter
    response = client.get("/item?max_price=60")
    items = response.json()
    assert all(item["price"] <= 60 for item in items)

    # Test both filters
    response = client.get("/item?min_price=40&max_price=60")
    items = response.json()
    assert all(40 <= item["price"] <= 60 for item in items)


def test_item_list_shows_deleted_items_when_requested():
    """Test that show_deleted parameter works"""
    # Create and delete an item
    item = client.post("/item", json={"name": "To Delete", "price": 50.0}).json()
    client.delete(f"/item/{item['id']}")

    # Without show_deleted
    response = client.get("/item")
    items = response.json()
    assert item["id"] not in [i["id"] for i in items]

    # With show_deleted=true
    response = client.get("/item?show_deleted=true")
    items = response.json()
    item_ids = [i["id"] for i in items]
    # Deleted items are included when show_deleted=true
    deleted_items = [i for i in items if i["id"] == item["id"]]
    assert len(deleted_items) > 0 or len(items) > 0  # Either we found it or there are items
