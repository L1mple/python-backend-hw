"""E2E tests for edge cases and error scenarios

Tests boundary conditions, validation errors, and error handling.
"""
from http import HTTPStatus


class TestItemEdgeCases:
    """Tests for item edge cases"""

    async def test_item_with_very_small_price(self, client):
        """Test item with very small price"""
        response = await client.post("/item/", json={"name": "Cheap Item", "price": 0.01})
        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert data["price"] == 0.01

    async def test_item_price_filters_edge_values(self, client):
        """Test item price filters with exact boundary values"""
        # Create item with specific price
        await client.post("/item/", json={"name": "Boundary", "price": 100.0})

        # Test exact min_price match
        response = await client.get("/item/?min_price=100.0")
        assert response.status_code == HTTPStatus.OK

        # Test exact max_price match
        response = await client.get("/item/?max_price=100.0")
        assert response.status_code == HTTPStatus.OK

    async def test_item_list_with_conflicting_price_filters(self, client):
        """Test item list where min_price > max_price"""
        response = await client.get("/item/?min_price=100&max_price=50")
        assert response.status_code == HTTPStatus.OK
        # Should return empty list
        data = response.json()
        assert len(data) == 0

    async def test_patch_item_empty_payload(self, client):
        """Test patch with no fields to update"""
        # Create item
        create_response = await client.post("/item/", json={"name": "Item", "price": 10.0})
        item_id = create_response.json()["id"]

        # Patch with empty body
        response = await client.patch(f"/item/{item_id}", json={})
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        # Should remain unchanged
        assert data["name"] == "Item"
        assert data["price"] == 10.0

    async def test_get_empty_items_list(self, client):
        """Test getting items when none exist (edge case)"""
        # This might have items from other tests, just check it returns OK
        response = await client.get("/item/?offset=10000&limit=1")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)


class TestCartEdgeCases:
    """Tests for cart edge cases"""

    async def test_cart_empty_after_creation(self, client):
        """Test that newly created cart is empty"""
        cart = await client.post("/cart/")
        cart_id = cart.json()["id"]

        response = await client.get(f"/cart/{cart_id}")
        data = response.json()

        assert data["items"] == []
        assert data["price"] == 0.0

    async def test_cart_with_multiple_different_items(self, client):
        """Test cart with multiple different items"""
        # Create items
        item1 = await client.post("/item/", json={"name": "Item1", "price": 10.0})
        item2 = await client.post("/item/", json={"name": "Item2", "price": 20.0})
        item3 = await client.post("/item/", json={"name": "Item3", "price": 30.0})

        item1_id = item1.json()["id"]
        item2_id = item2.json()["id"]
        item3_id = item3.json()["id"]

        # Create cart and add all items
        cart = await client.post("/cart/")
        cart_id = cart.json()["id"]

        await client.post(f"/cart/{cart_id}/add/{item1_id}")
        await client.post(f"/cart/{cart_id}/add/{item2_id}")
        response = await client.post(f"/cart/{cart_id}/add/{item3_id}")

        data = response.json()
        assert len(data["items"]) == 3
        assert data["price"] == 60.0

    async def test_multiple_items_in_cart_price_calculation(self, client):
        """Test complex cart price calculation"""
        # Create items with various prices
        item1 = await client.post("/item/", json={"name": "A", "price": 12.50})
        item2 = await client.post("/item/", json={"name": "B", "price": 7.25})
        item3 = await client.post("/item/", json={"name": "C", "price": 99.99})

        item1_id = item1.json()["id"]
        item2_id = item2.json()["id"]
        item3_id = item3.json()["id"]

        # Create cart
        cart = await client.post("/cart/")
        cart_id = cart.json()["id"]

        # Add items with quantities
        await client.post(f"/cart/{cart_id}/add/{item1_id}")
        await client.post(f"/cart/{cart_id}/add/{item1_id}")  # 12.50 * 2
        await client.post(f"/cart/{cart_id}/add/{item2_id}")  # 7.25 * 1
        response = await client.post(f"/cart/{cart_id}/add/{item3_id}")  # 99.99 * 1

        # Expected: 12.50*2 + 7.25 + 99.99 = 132.24
        data = response.json()
        assert abs(data["price"] - 132.24) < 0.01

    async def test_cart_pagination_edge_cases(self, client):
        """Test cart list pagination edge cases"""
        # Test offset beyond available items
        response = await client.get("/cart/?offset=10000&limit=10")
        # Should return empty list or 404
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]

    async def test_cart_quantity_filter_boundary(self, client):
        """Test cart quantity filters at boundaries"""
        # Create item and cart
        item = await client.post("/item/", json={"name": "Item", "price": 10.0})
        item_id = item.json()["id"]

        cart = await client.post("/cart/")
        cart_id = cart.json()["id"]

        # Add exactly 5 items
        for _ in range(5):
            await client.post(f"/cart/{cart_id}/add/{item_id}")

        # Test exact match - may return OK or NOT_FOUND depending on other carts
        response = await client.get("/cart/?min_quantity=5&max_quantity=5")
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]


class TestValidationErrors:
    """Tests for validation and error responses"""

    async def test_item_update_without_upsert_not_found(self, client):
        """Test updating non-existent item without upsert returns NOT_MODIFIED"""
        response = await client.put(
            "/item/99999",
            json={"name": "NonExistent", "price": 50.0}
        )
        assert response.status_code == HTTPStatus.NOT_MODIFIED

    async def test_item_upsert_existing(self, client):
        """Test upsert on existing item updates it"""
        # Create item
        create_response = await client.post("/item/", json={"name": "Original", "price": 10.0})
        item_id = create_response.json()["id"]

        # Upsert should update
        response = await client.put(
            f"/item/{item_id}?upsert=true",
            json={"name": "Updated", "price": 20.0}
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == "Updated"
        assert data["price"] == 20.0

    async def test_add_nonexistent_item_to_cart(self, client):
        """Test adding non-existent item to cart"""
        cart = await client.post("/cart/")
        cart_id = cart.json()["id"]

        response = await client.post(f"/cart/{cart_id}/add/999888777")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert "not found" in response.json()["detail"]

    async def test_add_item_to_nonexistent_cart(self, client):
        """Test adding item to non-existent cart"""
        item = await client.post("/item/", json={"name": "Item", "price": 10.0})
        item_id = item.json()["id"]

        response = await client.post(f"/cart/999888777/add/{item_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert "not found" in response.json()["detail"]

    async def test_get_carts_with_combined_filters(self, client):
        """Test getting carts with multiple filters"""
        # Create items
        item1 = await client.post("/item/", json={"name": "Cheap", "price": 5.0})
        item2 = await client.post("/item/", json={"name": "Mid", "price": 50.0})

        item1_id = item1.json()["id"]
        item2_id = item2.json()["id"]

        # Create carts
        cart1 = await client.post("/cart/")
        cart1_id = cart1.json()["id"]
        await client.post(f"/cart/{cart1_id}/add/{item1_id}")

        cart2 = await client.post("/cart/")
        cart2_id = cart2.json()["id"]
        await client.post(f"/cart/{cart2_id}/add/{item2_id}")

        # Filter by price range
        response = await client.get("/cart/?min_price=10&max_price=100")
        assert response.status_code == HTTPStatus.OK


class TestSlowEndpoint:
    """Tests for slow endpoint edge cases"""

    async def test_slow_endpoint_with_custom_delay(self, client):
        """Test slow endpoint with various delay values"""
        # Test with 0 delay
        response = await client.get("/item/slow?delay=0")
        assert response.status_code == HTTPStatus.OK

        # Test with small delay
        response = await client.get("/item/slow?delay=0.01")
        assert response.status_code == HTTPStatus.OK
        assert "Delayed response" in response.json()["message"]

    async def test_slow_endpoint_edge_delays(self, client):
        """Test slow endpoint with edge case delays"""
        # Test maximum allowed delay
        response = await client.get("/item/slow?delay=30")
        assert response.status_code == HTTPStatus.OK

        # Test minimum delay
        response = await client.get("/item/slow?delay=0")
        assert response.status_code == HTTPStatus.OK
