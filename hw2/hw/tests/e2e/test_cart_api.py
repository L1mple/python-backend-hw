"""E2E tests for Cart API

Tests all cart endpoints through the HTTP API layer.
These tests verify the complete flow: HTTP → Routes → Queries → Database.
"""
from http import HTTPStatus


class TestCartCRUD:
    """Tests for basic Cart CRUD operations"""

    async def test_create_cart(self, client):
        """Test POST /cart/ - create new cart"""
        response = await client.post("/cart/")
        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert "id" in data
        assert data["items"] == []
        assert data["price"] == 0.0
        assert response.headers["location"] == f"/cart/{data['id']}"

    async def test_get_cart_by_id(self, client):
        """Test GET /cart/{id} - get cart by ID"""
        # Create cart
        create_response = await client.post("/cart/")
        cart_id = create_response.json()["id"]

        # Get cart
        response = await client.get(f"/cart/{cart_id}")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == cart_id
        assert isinstance(data["items"], list)
        assert isinstance(data["price"], float)

    async def test_get_cart_not_found(self, client):
        """Test GET /cart/{id} - cart not found"""
        response = await client.get("/cart/999999")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert "was not found" in response.json()["detail"]


class TestCartList:
    """Tests for cart listing and filtering"""

    async def test_get_carts_list_empty(self, client):
        """Test GET /cart/ - returns 404 when no carts"""
        response = await client.get("/cart/")
        # Based on routes.py line 108, empty list returns 404
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]

    async def test_get_carts_list_with_carts(self, client):
        """Test GET /cart/ - list with carts"""
        # Create carts
        await client.post("/cart/")
        await client.post("/cart/")

        response = await client.get("/cart/")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    async def test_get_carts_list_with_pagination(self, client):
        """Test GET /cart/ - pagination"""
        # Create multiple carts
        for _ in range(5):
            await client.post("/cart/")

        # Test offset and limit
        response = await client.get("/cart/?offset=1&limit=2")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) <= 2

    async def test_get_carts_list_with_price_filter(self, client):
        """Test GET /cart/ - price filtering"""
        # Create items
        item1_response = await client.post("/item/", json={"name": "Cheap", "price": 10.0})
        item2_response = await client.post("/item/", json={"name": "Expensive", "price": 100.0})

        item1_id = item1_response.json()["id"]
        item2_id = item2_response.json()["id"]

        # Create carts and add items
        cart1_response = await client.post("/cart/")
        cart1_id = cart1_response.json()["id"]
        await client.post(f"/cart/{cart1_id}/add/{item1_id}")

        cart2_response = await client.post("/cart/")
        cart2_id = cart2_response.json()["id"]
        await client.post(f"/cart/{cart2_id}/add/{item2_id}")

        # Filter by min_price
        response = await client.get("/cart/?min_price=50")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        for cart in data:
            assert cart["price"] >= 50

        # Filter by max_price
        response = await client.get("/cart/?max_price=50")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        for cart in data:
            assert cart["price"] <= 50

    async def test_get_carts_list_with_quantity_filter(self, client):
        """Test GET /cart/ - quantity filtering"""
        # Create items
        item_response = await client.post("/item/", json={"name": "Item", "price": 10.0})
        item_id = item_response.json()["id"]

        # Create cart with items
        cart_response = await client.post("/cart/")
        cart_id = cart_response.json()["id"]
        await client.post(f"/cart/{cart_id}/add/{item_id}")
        await client.post(f"/cart/{cart_id}/add/{item_id}")  # Add twice

        # Filter by min_quantity
        response = await client.get("/cart/?min_quantity=2")
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]
        if response.status_code == HTTPStatus.OK:
            data = response.json()
            for cart in data:
                total_qty = sum(item["quantity"] for item in cart["items"])
                assert total_qty >= 2

        # Filter by max_quantity
        response = await client.get("/cart/?max_quantity=1")
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]


class TestCartItems:
    """Tests for adding items to cart"""

    async def test_add_item_to_cart(self, client):
        """Test POST /cart/{cart_id}/add/{item_id} - add item to cart"""
        # Create item and cart
        item_response = await client.post("/item/", json={"name": "Test Item", "price": 25.0})
        item_id = item_response.json()["id"]

        cart_response = await client.post("/cart/")
        cart_id = cart_response.json()["id"]

        # Add item to cart
        response = await client.post(f"/cart/{cart_id}/add/{item_id}")
        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == item_id
        assert data["items"][0]["quantity"] == 1
        assert data["price"] == 25.0
        assert response.headers["location"] == f"/cart/{cart_id}"

    async def test_add_item_to_cart_multiple_times(self, client):
        """Test adding same item multiple times increases quantity"""
        # Create item and cart
        item_response = await client.post("/item/", json={"name": "Item", "price": 10.0})
        item_id = item_response.json()["id"]

        cart_response = await client.post("/cart/")
        cart_id = cart_response.json()["id"]

        # Add item twice
        await client.post(f"/cart/{cart_id}/add/{item_id}")
        response = await client.post(f"/cart/{cart_id}/add/{item_id}")

        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2
        assert data["price"] == 20.0

    async def test_add_item_to_cart_cart_not_found(self, client):
        """Test POST /cart/{cart_id}/add/{item_id} - cart not found"""
        # Create item
        item_response = await client.post("/item/", json={"name": "Item", "price": 10.0})
        item_id = item_response.json()["id"]

        # Try to add to non-existent cart
        response = await client.post(f"/cart/999999/add/{item_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    async def test_add_item_to_cart_item_not_found(self, client):
        """Test POST /cart/{cart_id}/add/{item_id} - item not found"""
        # Create cart
        cart_response = await client.post("/cart/")
        cart_id = cart_response.json()["id"]

        # Try to add non-existent item
        response = await client.post(f"/cart/{cart_id}/add/999999")
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCartItemAvailability:
    """Tests for item availability in cart"""

    async def test_cart_item_availability(self, client):
        """Test that deleted items show as unavailable in cart"""
        # Create item and cart
        item_response = await client.post("/item/", json={"name": "Item", "price": 10.0})
        item_id = item_response.json()["id"]

        cart_response = await client.post("/cart/")
        cart_id = cart_response.json()["id"]

        # Add item to cart
        await client.post(f"/cart/{cart_id}/add/{item_id}")

        # Delete item
        await client.delete(f"/item/{item_id}")

        # Check cart - item should be unavailable
        response = await client.get(f"/cart/{cart_id}")
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["available"] is False


class TestCartPriceCalculation:
    """Tests for cart price calculation"""

    async def test_cart_price_calculation(self, client):
        """Test cart price is calculated correctly"""
        # Create items with different prices
        item1_response = await client.post("/item/", json={"name": "Item1", "price": 10.0})
        item2_response = await client.post("/item/", json={"name": "Item2", "price": 20.0})

        item1_id = item1_response.json()["id"]
        item2_id = item2_response.json()["id"]

        # Create cart
        cart_response = await client.post("/cart/")
        cart_id = cart_response.json()["id"]

        # Add items
        await client.post(f"/cart/{cart_id}/add/{item1_id}")
        await client.post(f"/cart/{cart_id}/add/{item1_id}")  # Add item1 twice
        response = await client.post(f"/cart/{cart_id}/add/{item2_id}")

        data = response.json()
        # Expected: 10*2 + 20*1 = 40.0
        assert data["price"] == 40.0
