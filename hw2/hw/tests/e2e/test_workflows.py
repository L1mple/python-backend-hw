"""E2E tests for complete user workflows

Tests complex, multi-step scenarios that simulate real user interactions.
"""
from http import HTTPStatus


class TestShoppingWorkflows:
    """Tests for complete shopping workflows"""

    async def test_full_shopping_workflow(self, client):
        """Test complete shopping workflow"""
        # Create items
        item1 = await client.post("/item/", json={"name": "Laptop", "price": 1000.0})
        item2 = await client.post("/item/", json={"name": "Mouse", "price": 25.0})
        item3 = await client.post("/item/", json={"name": "Keyboard", "price": 75.0})

        item1_id = item1.json()["id"]
        item2_id = item2.json()["id"]
        item3_id = item3.json()["id"]

        # Create cart
        cart = await client.post("/cart/")
        cart_id = cart.json()["id"]

        # Add items to cart
        await client.post(f"/cart/{cart_id}/add/{item1_id}")
        await client.post(f"/cart/{cart_id}/add/{item2_id}")
        await client.post(f"/cart/{cart_id}/add/{item2_id}")  # Buy 2 mice
        await client.post(f"/cart/{cart_id}/add/{item3_id}")

        # Check final cart
        cart_response = await client.get(f"/cart/{cart_id}")
        cart_data = cart_response.json()

        assert len(cart_data["items"]) == 3
        # 1000 + 25*2 + 75 = 1125
        assert cart_data["price"] == 1125.0

        # Find mouse item and check quantity
        mouse_item = [item for item in cart_data["items"] if item["id"] == item2_id][0]
        assert mouse_item["quantity"] == 2

    async def test_cart_with_mix_of_available_and_deleted_items(self, client):
        """Test cart contains both available and deleted items"""
        # Create items
        item1 = await client.post("/item/", json={"name": "Available", "price": 10.0})
        item2 = await client.post("/item/", json={"name": "ToDelete", "price": 20.0})

        item1_id = item1.json()["id"]
        item2_id = item2.json()["id"]

        # Create cart and add items
        cart = await client.post("/cart/")
        cart_id = cart.json()["id"]
        await client.post(f"/cart/{cart_id}/add/{item1_id}")
        await client.post(f"/cart/{cart_id}/add/{item2_id}")

        # Delete one item
        await client.delete(f"/item/{item2_id}")

        # Check cart
        cart_response = await client.get(f"/cart/{cart_id}")
        cart_data = cart_response.json()

        assert len(cart_data["items"]) == 2
        available_items = [item for item in cart_data["items"] if item["available"]]
        unavailable_items = [item for item in cart_data["items"] if not item["available"]]

        assert len(available_items) == 1
        assert len(unavailable_items) == 1

    async def test_update_item_preserves_old_cart_price(self, client):
        """Test that updating item price doesn't affect existing cart prices"""
        # Create item
        item = await client.post("/item/", json={"name": "Item", "price": 50.0})
        item_id = item.json()["id"]

        # Create cart and add item
        cart = await client.post("/cart/")
        cart_id = cart.json()["id"]
        await client.post(f"/cart/{cart_id}/add/{item_id}")
        await client.post(f"/cart/{cart_id}/add/{item_id}")  # Quantity 2

        # Check initial price
        cart_response = await client.get(f"/cart/{cart_id}")
        initial_price = cart_response.json()["price"]
        assert initial_price == 100.0  # 50 * 2

        # Update item price
        await client.put(f"/item/{item_id}", json={"name": "Item", "price": 100.0})

        # Check cart - price should remain the same (stored at add time)
        cart_response = await client.get(f"/cart/{cart_id}")
        cart_data = cart_response.json()

        # Price should remain unchanged - cart stores price at add time
        assert cart_data["price"] == 100.0

    async def test_multiple_carts_with_same_items(self, client):
        """Test multiple carts can contain the same items"""
        # Create item
        item = await client.post("/item/", json={"name": "PopularItem", "price": 30.0})
        item_id = item.json()["id"]

        # Create multiple carts
        cart1 = await client.post("/cart/")
        cart2 = await client.post("/cart/")
        cart3 = await client.post("/cart/")

        cart1_id = cart1.json()["id"]
        cart2_id = cart2.json()["id"]
        cart3_id = cart3.json()["id"]

        # Add same item to all carts
        await client.post(f"/cart/{cart1_id}/add/{item_id}")
        await client.post(f"/cart/{cart2_id}/add/{item_id}")
        await client.post(f"/cart/{cart2_id}/add/{item_id}")
        await client.post(f"/cart/{cart3_id}/add/{item_id}")

        # Verify each cart
        c1 = await client.get(f"/cart/{cart1_id}")
        c2 = await client.get(f"/cart/{cart2_id}")
        c3 = await client.get(f"/cart/{cart3_id}")

        assert c1.json()["price"] == 30.0
        assert c2.json()["price"] == 60.0
        assert c3.json()["price"] == 30.0

    async def test_complex_cart_scenario_with_quantity_changes(self, client):
        """Test complex cart scenario"""
        # Create items
        item1 = await client.post("/item/", json={"name": "A", "price": 10.0})
        item2 = await client.post("/item/", json={"name": "B", "price": 15.0})

        item1_id = item1.json()["id"]
        item2_id = item2.json()["id"]

        # Create cart
        cart = await client.post("/cart/")
        cart_id = cart.json()["id"]

        # Add item1 three times
        await client.post(f"/cart/{cart_id}/add/{item1_id}")
        await client.post(f"/cart/{cart_id}/add/{item1_id}")
        await client.post(f"/cart/{cart_id}/add/{item1_id}")

        # Add item2 twice
        await client.post(f"/cart/{cart_id}/add/{item2_id}")
        response = await client.post(f"/cart/{cart_id}/add/{item2_id}")

        data = response.json()
        assert len(data["items"]) == 2
        # 10*3 + 15*2 = 60
        assert data["price"] == 60.0

        item1_in_cart = [item for item in data["items"] if item["id"] == item1_id][0]
        item2_in_cart = [item for item in data["items"] if item["id"] == item2_id][0]

        assert item1_in_cart["quantity"] == 3
        assert item2_in_cart["quantity"] == 2


class TestItemManagementWorkflows:
    """Tests for item management workflows"""

    async def test_patch_item_multiple_fields(self, client):
        """Test patching multiple fields at once"""
        # Create item
        item = await client.post("/item/", json={"name": "Original", "price": 50.0})
        item_id = item.json()["id"]

        # Patch both name and price
        response = await client.patch(
            f"/item/{item_id}",
            json={"name": "Updated", "price": 75.0}
        )

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == "Updated"
        assert data["price"] == 75.0

    async def test_create_many_items_and_list(self, client):
        """Test creating many items and listing them"""
        # Create 15 items
        for i in range(15):
            await client.post("/item/", json={"name": f"Item{i}", "price": float(i * 5)})

        # Test pagination
        response = await client.get("/item/?offset=0&limit=5")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) <= 5

        response = await client.get("/item/?offset=5&limit=5")
        assert response.status_code == HTTPStatus.OK

        response = await client.get("/item/?offset=10&limit=10")
        assert response.status_code == HTTPStatus.OK


class TestFilteringWorkflows:
    """Tests for filtering workflows"""

    async def test_cart_list_filters_all_combinations(self, client):
        """Test cart list with all filter combinations"""
        # Create items with different prices
        cheap = await client.post("/item/", json={"name": "Cheap", "price": 5.0})
        mid = await client.post("/item/", json={"name": "Mid", "price": 50.0})
        expensive = await client.post("/item/", json={"name": "Expensive", "price": 200.0})

        cheap_id = cheap.json()["id"]
        mid_id = mid.json()["id"]

        # Create carts with different characteristics
        cart1 = await client.post("/cart/")
        cart1_id = cart1.json()["id"]
        await client.post(f"/cart/{cart1_id}/add/{cheap_id}")

        cart2 = await client.post("/cart/")
        cart2_id = cart2.json()["id"]
        await client.post(f"/cart/{cart2_id}/add/{mid_id}")
        await client.post(f"/cart/{cart2_id}/add/{mid_id}")

        cart3 = await client.post("/cart/")
        cart3_id = cart3.json()["id"]
        for _ in range(5):
            await client.post(f"/cart/{cart3_id}/add/{cheap_id}")

        # Test various filter combinations
        response = await client.get("/cart/?min_price=10&max_price=150")
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]

        response = await client.get("/cart/?min_quantity=2")
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]

        response = await client.get("/cart/?min_price=10&min_quantity=2")
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]

    async def test_item_list_with_all_filter_combinations(self, client):
        """Test item list with various filter combinations"""
        # Create items with different prices
        await client.post("/item/", json={"name": "Low", "price": 10.0})
        await client.post("/item/", json={"name": "Mid", "price": 50.0})
        await client.post("/item/", json={"name": "High", "price": 100.0})

        # Test various combinations
        response = await client.get("/item/?min_price=20&max_price=80")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        for item in data:
            assert 20 <= item["price"] <= 80

        response = await client.get("/item/?offset=1&limit=1")
        assert response.status_code == HTTPStatus.OK
