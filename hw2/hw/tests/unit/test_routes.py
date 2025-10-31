"""Unit tests for API routes

Tests the route handlers in shop_api/api/shop/routes.py.
Most functional testing is done in E2E tests. These tests cover specific edge cases.
"""
import pytest
from http import HTTPStatus
from unittest.mock import AsyncMock, Mock, patch


class TestItemRoutes:
    """Tests for item route handlers"""

    async def test_post_item_returns_entity(self, client):
        """Test POST /item/ returns entity with proper response"""
        response = await client.post("/item/", json={"name": "Test", "price": 10.0})
        assert response.status_code == HTTPStatus.CREATED
        assert "location" in response.headers

    async def test_get_item_deleted_not_found(self, client):
        """Test GET /item/{id} returns 404 for deleted item"""
        create_resp = await client.post("/item/", json={"name": "Temp", "price": 5.0})
        item_id = create_resp.json()["id"]
        await client.delete(f"/item/{item_id}")

        response = await client.get(f"/item/{item_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    async def test_get_items_list_returns_empty_list(self, client):
        """Test GET /item/ can return empty list"""
        response = await client.get("/item/?min_price=999999999")
        assert response.status_code == HTTPStatus.OK
        assert isinstance(response.json(), list)

    async def test_put_item_upsert_false_returns_none(self, client):
        """Test PUT /item/{id} without upsert when item doesn't exist"""
        response = await client.put(
            "/item/88888888",
            json={"name": "Test", "price": 10.0}
        )
        assert response.status_code == HTTPStatus.NOT_MODIFIED

    async def test_put_item_upsert_true_branches(self, client):
        """Test PUT /item/{id}?upsert=true both branches"""
        # Branch 1: upsert creates new
        resp1 = await client.put(
            "/item/77777777?upsert=true",
            json={"name": "New", "price": 20.0}
        )
        assert resp1.status_code == HTTPStatus.OK

        # Branch 2: upsert updates existing
        create_resp = await client.post("/item/", json={"name": "Existing", "price": 10.0})
        item_id = create_resp.json()["id"]

        resp2 = await client.put(
            f"/item/{item_id}?upsert=true",
            json={"name": "Updated", "price": 30.0}
        )
        assert resp2.status_code == HTTPStatus.OK

    async def test_patch_item_existing_deleted_check(self, client):
        """Test PATCH /item/{id} with existing deleted item"""
        create_resp = await client.post("/item/", json={"name": "Item", "price": 10.0})
        item_id = create_resp.json()["id"]
        await client.delete(f"/item/{item_id}")

        response = await client.patch(f"/item/{item_id}", json={"name": "New"})
        assert response.status_code == HTTPStatus.NOT_MODIFIED

    async def test_patch_item_entity_none_path(self, client):
        """Test PATCH /item/{id} when patch returns None"""
        response = await client.patch("/item/55555555", json={"name": "Test"})
        assert response.status_code == HTTPStatus.NOT_MODIFIED

    async def test_delete_item_not_found_path(self, client):
        """Test DELETE /item/{id} when item not found"""
        response = await client.delete("/item/44444444")
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCartRoutes:
    """Tests for cart route handlers"""

    async def test_post_cart_returns_entity(self, client):
        """Test POST /cart/ returns entity with proper response"""
        response = await client.post("/cart/")
        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert "id" in data
        assert "location" in response.headers

    async def test_get_cart_entity_not_found_path(self, client):
        """Test GET /cart/{id} not found exception path"""
        response = await client.get("/cart/99999999")
        assert response.status_code == HTTPStatus.NOT_FOUND

    async def test_get_carts_list_empty_raises_404(self, client):
        """Test GET /cart/ with no results"""
        response = await client.get("/cart/?min_price=99999999")
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND]

    async def test_add_item_to_cart_not_found_paths(self, client):
        """Test POST /cart/{cart_id}/add/{item_id} not found paths"""
        response = await client.post("/cart/99999999/add/88888888")
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestSlowEndpoint:
    """Tests for slow endpoint"""

    async def test_slow_endpoint_default(self, client):
        """Test GET /item/slow with default delay parameter"""
        response = await client.get("/item/slow")
        assert response.status_code == HTTPStatus.OK
        assert "Delayed response" in response.json()["message"]


class TestEdgeCaseCoverage:
    """Tests to cover edge cases in routes.py"""

    async def test_get_carts_empty_list_returns_404(self, client):
        """Test GET /cart/ returns 404 when list is empty"""
        with patch("shop_api.data.cart_queries.get_many") as mock_get:
            mock_get.return_value = []
            response = await client.get("/cart/")
            assert response.status_code == HTTPStatus.NOT_FOUND

    async def test_get_cart_by_id_ok(self, client):
        """Test GET /cart/{id} returns cart"""
        from shop_api.data.models import CartEntity, CartInfo

        with patch("shop_api.data.cart_queries.get_one") as mock_get:
            entity = CartEntity(id=1, info=CartInfo(items=[], price=0.0))
            mock_get.return_value = entity
            response = await client.get("/cart/1")
            assert response.status_code == HTTPStatus.OK

    async def test_post_cart_ok(self, client):
        """Test POST /cart/ creates cart"""
        from shop_api.data.models import CartEntity, CartInfo

        with patch("shop_api.data.cart_queries.add") as mock_add:
            mock_entity = Mock()
            mock_entity.id = 42
            mock_entity.info = CartInfo(items=[], price=0.0)
            mock_add.return_value = mock_entity
            response = await client.post("/cart/")
            assert response.status_code == HTTPStatus.CREATED

    async def test_add_item_to_cart_ok(self, client):
        """Test POST /cart/{cart_id}/add/{item_id} works"""
        from shop_api.data.models import CartEntity, CartInfo

        with patch("shop_api.data.cart_queries.add_item_to_cart") as mock_add:
            entity = CartEntity(id=1, info=CartInfo(items=[], price=0.0))
            mock_add.return_value = entity
            response = await client.post("/cart/1/add/2")
            assert response.status_code == HTTPStatus.CREATED

    async def test_get_item_by_id_ok(self, client):
        """Test GET /item/{id} returns item"""
        from shop_api.data.models import ItemEntity, ItemInfo

        with patch("shop_api.data.item_queries.get_one") as mock_get:
            entity = ItemEntity(id=1, info=ItemInfo(name="Test", price=10.0, deleted=False))
            mock_get.return_value = entity
            response = await client.get("/item/1")
            assert response.status_code == HTTPStatus.OK

    async def test_get_items_list_ok(self, client):
        """Test GET /item/ returns list"""
        from shop_api.data.models import ItemEntity, ItemInfo

        with patch("shop_api.data.item_queries.get_many") as mock_get:
            entity = ItemEntity(id=1, info=ItemInfo(name="Test", price=10.0, deleted=False))
            mock_get.return_value = [entity]
            response = await client.get("/item/")
            assert response.status_code == HTTPStatus.OK

    async def test_put_item_ok(self, client):
        """Test PUT /item/{id} updates item"""
        from shop_api.data.models import ItemEntity, ItemInfo

        with patch("shop_api.data.item_queries.get_one") as mock_get, \
             patch("shop_api.data.item_queries.update") as mock_update:
            entity = ItemEntity(id=1, info=ItemInfo(name="Test", price=10.0, deleted=False))
            mock_get.return_value = entity
            mock_update.return_value = entity
            response = await client.put("/item/1", json={"name": "New", "price": 20.0})
            assert response.status_code == HTTPStatus.OK

    async def test_put_item_update_returns_none(self, client):
        """Test PUT /item/{id} when update returns None"""
        from shop_api.data.models import ItemEntity, ItemInfo

        with patch("shop_api.data.item_queries.get_one") as mock_get, \
             patch("shop_api.data.item_queries.update") as mock_update:
            entity = ItemEntity(id=1, info=ItemInfo(name="Test", price=10.0, deleted=False))
            mock_get.return_value = entity
            mock_update.return_value = None

            response = await client.put("/item/1", json={"name": "New", "price": 20.0})
            assert response.status_code == HTTPStatus.NOT_MODIFIED

    async def test_patch_item_ok(self, client):
        """Test PATCH /item/{id} patches item"""
        from shop_api.data.models import ItemEntity, ItemInfo

        with patch("shop_api.data.item_queries.get_one") as mock_get, \
             patch("shop_api.data.item_queries.patch") as mock_patch:
            entity = ItemEntity(id=1, info=ItemInfo(name="Test", price=10.0, deleted=False))
            mock_get.return_value = entity
            mock_patch.return_value = entity
            response = await client.patch("/item/1", json={"name": "New"})
            assert response.status_code == HTTPStatus.OK

    async def test_patch_item_patch_returns_none(self, client):
        """Test PATCH /item/{id} when patch returns None"""
        from shop_api.data.models import ItemEntity, ItemInfo

        with patch("shop_api.data.item_queries.get_one") as mock_get, \
             patch("shop_api.data.item_queries.patch") as mock_patch:
            entity = ItemEntity(id=1, info=ItemInfo(name="Test", price=10.0, deleted=False))
            mock_get.return_value = entity
            mock_patch.return_value = None

            response = await client.patch("/item/1", json={"name": "New"})
            assert response.status_code == HTTPStatus.NOT_MODIFIED

    async def test_delete_item_ok(self, client):
        """Test DELETE /item/{id} deletes item"""
        from shop_api.data.models import ItemEntity, ItemInfo

        with patch("shop_api.data.item_queries.delete") as mock_delete:
            entity = ItemEntity(id=1, info=ItemInfo(name="Test", price=10.0, deleted=True))
            mock_delete.return_value = entity
            response = await client.delete("/item/1")
            assert response.status_code == HTTPStatus.OK

    async def test_post_item_ok(self, client):
        """Test POST /item/ creates item"""
        from shop_api.data.models import ItemEntity, ItemInfo

        with patch("shop_api.data.item_queries.add") as mock_add:
            entity = ItemEntity(id=99, info=ItemInfo(name="Test", price=10.0, deleted=False))
            mock_add.return_value = entity
            response = await client.post("/item/", json={"name": "Test", "price": 10.0})
            assert response.status_code == HTTPStatus.CREATED
