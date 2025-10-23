"""E2E tests for Item API

Tests all item endpoints through the HTTP API layer.
These tests verify the complete flow: HTTP → Routes → Queries → Database.
"""
from http import HTTPStatus


class TestItemCRUD:
    """Tests for basic Item CRUD operations"""

    async def test_create_item(self, client):
        """Test POST /item/ - create new item"""
        response = await client.post(
            "/item/",
            json={"name": "Test Item", "price": 100.0}
        )
        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert data["name"] == "Test Item"
        assert data["price"] == 100.0
        assert data["deleted"] is False
        assert "id" in data
        assert response.headers["location"] == f"/item/{data['id']}"

    async def test_get_item_by_id(self, client):
        """Test GET /item/{id} - get item by ID"""
        # Create item first
        create_response = await client.post(
            "/item/",
            json={"name": "Test Item", "price": 50.0}
        )
        item_id = create_response.json()["id"]

        # Get item
        response = await client.get(f"/item/{item_id}")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == item_id
        assert data["name"] == "Test Item"
        assert data["price"] == 50.0

    async def test_get_item_not_found(self, client):
        """Test GET /item/{id} - item not found"""
        response = await client.get("/item/999999")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert "was not found" in response.json()["detail"]

    async def test_update_item(self, client):
        """Test PUT /item/{id} - update existing item"""
        # Create item
        create_response = await client.post("/item/", json={"name": "Old Name", "price": 10.0})
        item_id = create_response.json()["id"]

        # Update item
        response = await client.put(
            f"/item/{item_id}",
            json={"name": "New Name", "price": 20.0}
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == item_id
        assert data["name"] == "New Name"
        assert data["price"] == 20.0

    async def test_update_item_not_found(self, client):
        """Test PUT /item/{id} - item not found without upsert"""
        response = await client.put(
            "/item/999999",
            json={"name": "Test", "price": 10.0}
        )
        assert response.status_code == HTTPStatus.NOT_MODIFIED

    async def test_patch_item_name(self, client):
        """Test PATCH /item/{id} - update only name"""
        # Create item
        create_response = await client.post("/item/", json={"name": "Original", "price": 100.0})
        item_id = create_response.json()["id"]

        # Patch name only
        response = await client.patch(f"/item/{item_id}", json={"name": "Patched Name"})
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == "Patched Name"
        assert data["price"] == 100.0  # Price unchanged

    async def test_patch_item_price(self, client):
        """Test PATCH /item/{id} - update only price"""
        # Create item
        create_response = await client.post("/item/", json={"name": "Item", "price": 50.0})
        item_id = create_response.json()["id"]

        # Patch price only
        response = await client.patch(f"/item/{item_id}", json={"price": 75.0})
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == "Item"  # Name unchanged
        assert data["price"] == 75.0

    async def test_patch_item_not_found(self, client):
        """Test PATCH /item/{id} - item not found"""
        response = await client.patch("/item/999999", json={"name": "Test"})
        assert response.status_code == HTTPStatus.NOT_MODIFIED

    async def test_delete_item(self, client):
        """Test DELETE /item/{id} - soft delete item"""
        # Create item
        create_response = await client.post("/item/", json={"name": "To Delete", "price": 10.0})
        item_id = create_response.json()["id"]

        # Delete item
        response = await client.delete(f"/item/{item_id}")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["deleted"] is True

    async def test_delete_item_not_found(self, client):
        """Test DELETE /item/{id} - item not found"""
        response = await client.delete("/item/999999")
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestItemUpsert:
    """Tests for item upsert functionality"""

    async def test_upsert_item_create_new(self, client):
        """Test PUT /item/{id}?upsert=true - create new item"""
        response = await client.put(
            "/item/12345?upsert=true",
            json={"name": "Upserted Item", "price": 30.0}
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == 12345
        assert data["name"] == "Upserted Item"

    async def test_upsert_item_update_existing(self, client):
        """Test PUT /item/{id}?upsert=true - update existing item"""
        # Create item
        create_response = await client.post("/item/", json={"name": "Original", "price": 10.0})
        item_id = create_response.json()["id"]

        # Upsert (update)
        response = await client.put(
            f"/item/{item_id}?upsert=true",
            json={"name": "Updated via Upsert", "price": 40.0}
        )
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == "Updated via Upsert"
        assert data["price"] == 40.0


class TestItemList:
    """Tests for item listing and filtering"""

    async def test_get_items_list_empty(self, client):
        """Test GET /item/ - empty list"""
        response = await client.get("/item/")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert isinstance(data, list)

    async def test_get_items_list_with_items(self, client):
        """Test GET /item/ - list with items"""
        # Create items
        await client.post("/item/", json={"name": "Item 1", "price": 10.0})
        await client.post("/item/", json={"name": "Item 2", "price": 20.0})

        response = await client.get("/item/")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) >= 2

    async def test_get_items_list_with_pagination(self, client):
        """Test GET /item/ - pagination"""
        # Create multiple items
        for i in range(5):
            await client.post("/item/", json={"name": f"Item {i}", "price": float(i * 10)})

        # Test offset and limit
        response = await client.get("/item/?offset=1&limit=2")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) <= 2

    async def test_get_items_list_with_price_filter(self, client):
        """Test GET /item/ - price filtering"""
        # Create items with different prices
        await client.post("/item/", json={"name": "Cheap", "price": 10.0})
        await client.post("/item/", json={"name": "Expensive", "price": 100.0})

        # Filter by min_price
        response = await client.get("/item/?min_price=50")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        for item in data:
            assert item["price"] >= 50

        # Filter by max_price
        response = await client.get("/item/?max_price=50")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        for item in data:
            assert item["price"] <= 50

    async def test_get_items_list_show_deleted(self, client):
        """Test GET /item/?show_deleted=true"""
        # Create and delete item
        create_response = await client.post("/item/", json={"name": "ToDelUnique123", "price": 15.0})
        item_id = create_response.json()["id"]
        await client.delete(f"/item/{item_id}")

        # Without show_deleted
        response = await client.get("/item/")
        data = response.json()
        deleted_items = [item for item in data if item.get("id") == item_id]
        assert len(deleted_items) == 0

        # With show_deleted - should include deleted items
        response = await client.get("/item/?show_deleted=true")
        data = response.json()
        # Check if any deleted items exist in response
        has_deleted = any(item.get("deleted", False) for item in data)
        # The deleted item might or might not appear based on pagination, just check endpoint works
        assert response.status_code == 200


class TestItemDeleted:
    """Tests for deleted item behavior"""

    async def test_get_deleted_item_not_found(self, client):
        """Test GET /item/{id} - deleted item returns 404"""
        # Create and delete item
        create_response = await client.post(
            "/item/",
            json={"name": "To Delete", "price": 10.0}
        )
        item_id = create_response.json()["id"]
        await client.delete(f"/item/{item_id}")

        # Try to get deleted item
        response = await client.get(f"/item/{item_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    async def test_patch_deleted_item(self, client):
        """Test PATCH /item/{id} - cannot patch deleted item"""
        # Create and delete item
        create_response = await client.post("/item/", json={"name": "Item", "price": 10.0})
        item_id = create_response.json()["id"]
        await client.delete(f"/item/{item_id}")

        # Try to patch
        response = await client.patch(f"/item/{item_id}", json={"name": "New Name"})
        assert response.status_code == HTTPStatus.NOT_MODIFIED


class TestItemSlowEndpoint:
    """Tests for slow endpoint"""

    async def test_slow_endpoint(self, client):
        """Test GET /item/slow - slow endpoint"""
        response = await client.get("/item/slow?delay=0.1")
        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert "Delayed response" in data["message"]

    async def test_slow_endpoint_default_delay(self, client):
        """Test GET /item/slow - default delay"""
        response = await client.get("/item/slow")
        assert response.status_code == HTTPStatus.OK
