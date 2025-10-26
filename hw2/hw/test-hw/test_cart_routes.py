"""Tests for shop_api.cart_routes module"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from http import HTTPStatus
from shop_api.main import app
from shop_api.store.storage import CartData, ItemnInCartData


client = TestClient(app)


class TestPostCart:
    """Test POST /cart endpoint"""

    @patch("shop_api.cart_routes.DBStorage")
    @patch("shop_api.cart_routes.get_db")
    def test_post_cart_success(self, mock_get_db, mock_storage_class):
        """Test creating cart successfully"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.create_cart.return_value = CartData(id=123, items=[], price=0.0)
        mock_storage_class.return_value = mock_storage

        response = client.post("/cart")

        assert response.status_code == HTTPStatus.CREATED
        assert "location" in response.headers
        assert response.headers["location"] == "/cart/123"
        data = response.json()
        assert data["id"] == 123


class TestAddItemToCart:
    """Test POST /cart/{cart_id}/add/{item_id} endpoint"""

    @patch("shop_api.cart_routes.DBStorage")
    @patch("shop_api.cart_routes.get_db")
    def test_add_item_to_cart_success(self, mock_get_db, mock_storage_class):
        """Test adding item to cart successfully"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.add_item_to_cart.return_value = True
        mock_storage_class.return_value = mock_storage

        response = client.post("/cart/1/add/10")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["message"] == "Item added to cart"
        mock_storage.add_item_to_cart.assert_called_once_with(1, 10)

    @patch("shop_api.cart_routes.DBStorage")
    @patch("shop_api.cart_routes.get_db")
    def test_add_item_to_cart_not_found(self, mock_get_db, mock_storage_class):
        """Test adding item to non-existent cart or item"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.add_item_to_cart.return_value = False
        mock_storage_class.return_value = mock_storage

        response = client.post("/cart/999/add/999")

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestGetCart:
    """Test GET /cart/{cart_id} endpoint"""

    @patch("shop_api.cart_routes.DBStorage")
    @patch("shop_api.cart_routes.get_db")
    def test_get_cart_empty(self, mock_get_db, mock_storage_class):
        """Test getting empty cart"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.get_cart.return_value = CartData(id=1, items=[], price=0.0)
        mock_storage_class.return_value = mock_storage

        response = client.get("/cart/1")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == 1
        assert data["items"] == []
        assert data["price"] == 0.0

    @patch("shop_api.cart_routes.DBStorage")
    @patch("shop_api.cart_routes.get_db")
    def test_get_cart_with_items(self, mock_get_db, mock_storage_class):
        """Test getting cart with items"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.get_cart.return_value = CartData(
            id=1,
            items=[
                ItemnInCartData(id=10, name="Item1", quantity=2, available=True),
                ItemnInCartData(id=20, name="Item2", quantity=1, available=False),
            ],
            price=50.0,
        )
        mock_storage_class.return_value = mock_storage

        response = client.get("/cart/1")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == 1
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] == 10
        assert data["items"][0]["quantity"] == 2
        assert data["items"][0]["available"] is True
        assert data["items"][1]["available"] is False
        assert data["price"] == 50.0

    @patch("shop_api.cart_routes.DBStorage")
    @patch("shop_api.cart_routes.get_db")
    def test_get_cart_not_found(self, mock_get_db, mock_storage_class):
        """Test getting non-existent cart"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.get_cart.side_effect = KeyError("Cart not found")
        mock_storage_class.return_value = mock_storage

        response = client.get("/cart/999")

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestGetCartList:
    """Test GET /cart endpoint"""

    @patch("shop_api.cart_routes.DBStorage")
    @patch("shop_api.cart_routes.get_db")
    def test_get_cart_list_success(self, mock_get_db, mock_storage_class):
        """Test getting cart list"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.get_carts.return_value = [
            CartData(id=1, items=[], price=0.0),
            CartData(
                id=2,
                items=[ItemnInCartData(id=1, name="Item", quantity=2, available=True)],
                price=20.0,
            ),
        ]
        mock_storage_class.return_value = mock_storage

        response = client.get("/cart")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2
        assert data[1]["price"] == 20.0

    @patch("shop_api.cart_routes.DBStorage")
    @patch("shop_api.cart_routes.get_db")
    def test_get_cart_list_with_filters(self, mock_get_db, mock_storage_class):
        """Test getting cart list with filters"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.get_carts.return_value = [
            CartData(id=1, items=[], price=50.0),
        ]
        mock_storage_class.return_value = mock_storage

        response = client.get("/cart?min_price=30&max_price=100")

        assert response.status_code == HTTPStatus.OK
        mock_storage.get_carts.assert_called_once()

    @patch("shop_api.cart_routes.DBStorage")
    @patch("shop_api.cart_routes.get_db")
    def test_get_cart_list_with_quantity_filters(self, mock_get_db, mock_storage_class):
        """Test getting cart list with quantity filters"""
        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        mock_storage.get_carts.return_value = []
        mock_storage_class.return_value = mock_storage

        response = client.get("/cart?min_quantity=1&max_quantity=10")

        assert response.status_code == HTTPStatus.OK
        call_kwargs = mock_storage.get_carts.call_args.kwargs
        assert call_kwargs["min_quantity"] == 1
        assert call_kwargs["max_quantity"] == 10

    @patch("shop_api.cart_routes.get_db")
    def test_get_cart_list_invalid_offset(self, mock_get_db):
        """Test getting cart list with invalid offset"""
        response = client.get("/cart?offset=-1")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @patch("shop_api.cart_routes.get_db")
    def test_get_cart_list_invalid_limit(self, mock_get_db):
        """Test getting cart list with invalid limit"""
        response = client.get("/cart?limit=0")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @patch("shop_api.cart_routes.get_db")
    def test_get_cart_list_invalid_min_price(self, mock_get_db):
        """Test getting cart list with invalid min_price"""
        response = client.get("/cart?min_price=-10")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    @patch("shop_api.cart_routes.get_db")
    def test_get_cart_list_invalid_min_quantity(self, mock_get_db):
        """Test getting cart list with invalid min_quantity"""
        response = client.get("/cart?min_quantity=-1")
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
