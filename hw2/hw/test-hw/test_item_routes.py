"""Tests for shop_api.item_routes module"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException
from http import HTTPStatus
from shop_api.main import app
from shop_api.store.storage import ItemData
from shop_api.contracts import ItemRequest, ItemPatchRequest


client = TestClient(app)


class TestPostItem:
    """Test POST /item endpoint"""

    @patch("shop_api.item_routes.DBStorage")
    @patch("shop_api.item_routes.get_db")
    def test_post_item_success(self, mock_get_db, mock_storage_class):
        """Test creating item successfully"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.add_item.return_value = ItemData(
            id=1, name="Test Item", price=10.99, deleted=False
        )
        mock_storage_class.return_value = mock_storage

        response = client.post("/item", json={"name": "Test Item", "price": 10.99})

        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Test Item"
        assert data["price"] == 10.99
        assert data["deleted"] is False

    @patch("shop_api.item_routes.get_db")
    def test_post_item_invalid_price(self, mock_get_db):
        """Test creating item with invalid price"""
        response = client.post("/item", json={"name": "Test", "price": -5.0})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @patch("shop_api.item_routes.get_db")
    def test_post_item_missing_name(self, mock_get_db):
        """Test creating item without name"""
        response = client.post("/item", json={"price": 10.0})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestGetItem:
    """Test GET /item/{item_id} endpoint"""

    @patch("shop_api.item_routes.DBStorage")
    @patch("shop_api.item_routes.get_db")
    def test_get_item_success(self, mock_get_db, mock_storage_class):
        """Test getting item successfully"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.get_item.return_value = ItemData(
            id=1, name="Item", price=15.0, deleted=False
        )
        mock_storage_class.return_value = mock_storage

        response = client.get("/item/1")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Item"

    @patch("shop_api.item_routes.DBStorage")
    @patch("shop_api.item_routes.get_db")
    def test_get_item_not_found(self, mock_get_db, mock_storage_class):
        """Test getting non-existent item"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.get_item.side_effect = KeyError("Item not found")
        mock_storage_class.return_value = mock_storage

        response = client.get("/item/999")

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestGetItemList:
    """Test GET /item endpoint"""

    @patch("shop_api.item_routes.DBStorage")
    @patch("shop_api.item_routes.get_db")
    def test_get_item_list_success(self, mock_get_db, mock_storage_class):
        """Test getting item list"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.get_items.return_value = [
            ItemData(id=1, name="Item1", price=10.0, deleted=False),
            ItemData(id=2, name="Item2", price=20.0, deleted=False),
        ]
        mock_storage_class.return_value = mock_storage

        response = client.get("/item")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2

    @patch("shop_api.item_routes.DBStorage")
    @patch("shop_api.item_routes.get_db")
    def test_get_item_list_with_filters(self, mock_get_db, mock_storage_class):
        """Test getting item list with filters"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.get_items.return_value = [
            ItemData(id=1, name="Item1", price=15.0, deleted=False),
        ]
        mock_storage_class.return_value = mock_storage

        response = client.get("/item?min_price=10&max_price=20")

        assert response.status_code == HTTPStatus.OK
        mock_storage.get_items.assert_called_once()

    @patch("shop_api.item_routes.get_db")
    def test_get_item_list_invalid_offset(self, mock_get_db):
        """Test getting item list with invalid offset"""
        response = client.get("/item?offset=-1")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @patch("shop_api.item_routes.get_db")
    def test_get_item_list_invalid_limit(self, mock_get_db):
        """Test getting item list with invalid limit"""
        response = client.get("/item?limit=0")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestPutItem:
    """Test PUT /item/{item_id} endpoint"""

    @patch("shop_api.item_routes.DBStorage")
    @patch("shop_api.item_routes.get_db")
    def test_put_item_success(self, mock_get_db, mock_storage_class):
        """Test updating item with put"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.put_item.return_value = ItemData(
            id=1, name="Updated", price=25.0, deleted=False
        )
        mock_storage_class.return_value = mock_storage

        response = client.put("/item/1", json={"name": "Updated", "price": 25.0})

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == "Updated"
        assert data["price"] == 25.0

    @patch("shop_api.item_routes.get_db")
    def test_put_item_missing_fields(self, mock_get_db):
        """Test put without required fields"""
        response = client.put("/item/1", json={"name": "Test"})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestPatchItem:
    """Test PATCH /item/{item_id} endpoint"""

    @patch("shop_api.item_routes.DBStorage")
    @patch("shop_api.item_routes.get_db")
    def test_patch_item_success(self, mock_get_db, mock_storage_class):
        """Test patching item successfully"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.patch_item.return_value = ItemData(
            id=1, name="Patched", price=15.0, deleted=False
        )
        mock_storage_class.return_value = mock_storage

        response = client.patch("/item/1", json={"name": "Patched"})

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == "Patched"

    @patch("shop_api.item_routes.DBStorage")
    @patch("shop_api.item_routes.get_db")
    def test_patch_item_deleted(self, mock_get_db, mock_storage_class):
        """Test patching deleted item returns NOT_MODIFIED"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.patch_item.return_value = ItemData(
            id=1, name="Item", price=10.0, deleted=True
        )
        mock_storage_class.return_value = mock_storage

        response = client.patch("/item/1", json={"name": "New"})

        assert response.status_code == HTTPStatus.NOT_MODIFIED

    @patch("shop_api.item_routes.get_db")
    def test_patch_item_extra_field(self, mock_get_db):
        """Test patch with extra field"""
        response = client.patch("/item/1", json={"name": "Test", "extra": "field"})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestDeleteItem:
    """Test DELETE /item/{item_id} endpoint"""

    @patch("shop_api.item_routes.DBStorage")
    @patch("shop_api.item_routes.get_db")
    def test_delete_item_success(self, mock_get_db, mock_storage_class):
        """Test deleting item successfully"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.soft_delete_item.return_value = ItemData(
            id=1, name="Item", price=10.0, deleted=True
        )
        mock_storage_class.return_value = mock_storage

        response = client.delete("/item/1")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["deleted"] is True
