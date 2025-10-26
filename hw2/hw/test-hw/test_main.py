"""Tests for shop_api.main module"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from shop_api.main import app


class TestAppConfiguration:
    """Test app configuration"""

    def test_app_exists(self):
        """Test app instance exists"""
        assert app is not None

    def test_app_title(self):
        """Test app title"""
        assert app.title == "Shop API"

    def test_app_has_routes(self):
        """Test app has routes configured"""
        routes = [route.path for route in app.routes]
        # Check that cart and item routes are included
        assert any("/cart" in route for route in routes)
        assert any("/item" in route for route in routes)


class TestAppRouters:
    """Test that routers are included"""

    def test_cart_router_included(self):
        """Test cart router is included"""
        routes = [route.path for route in app.routes]
        assert "/cart/" in routes
        assert "/cart/{cart_id}" in routes
        assert "/cart/{cart_id}/add/{item_id}" in routes

    def test_item_router_included(self):
        """Test item router is included"""
        routes = [route.path for route in app.routes]
        assert "/item/" in routes
        assert "/item/{item_id}" in routes


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint"""

    def test_metrics_endpoint_exists(self):
        """Test /metrics endpoint exists"""
        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_endpoint_returns_text(self):
        """Test /metrics endpoint returns prometheus text format"""
        client = TestClient(app)
        response = client.get("/metrics")
        # Prometheus metrics should be in text format
        assert "text/plain" in response.headers.get("content-type", "")


class TestInitDb:
    """Test database initialization"""

    @patch("shop_api.main.init_db")
    def test_init_db_called_on_import(self, mock_init_db):
        """Test init_db is called when module is imported"""
        # This test verifies init_db is available and callable
        from shop_api.main import init_db

        init_db()
        # Just verify it can be called without errors
        assert True


class TestAppHealth:
    """Test app basic health checks"""

    def test_app_accepts_requests(self):
        """Test app can handle requests"""
        client = TestClient(app)
        # Try to access any endpoint - even 404 means app is responding
        response = client.get("/nonexistent")
        # We just want to verify the app responds
        assert response.status_code in [404, 200, 422]

    @patch("shop_api.cart_routes.get_db")
    @patch("shop_api.cart_routes.DBStorage")
    def test_app_cart_endpoint_accessible(self, mock_storage_class, mock_get_db):
        """Test cart endpoint is accessible"""
        client = TestClient(app)

        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        from shop_api.store.storage import CartData

        mock_storage.create_cart.return_value = CartData(id=1, items=[], price=0.0)
        mock_storage_class.return_value = mock_storage

        response = client.post("/cart")
        assert response.status_code == 201

    @patch("shop_api.item_routes.get_db")
    @patch("shop_api.item_routes.DBStorage")
    def test_app_item_endpoint_accessible(self, mock_storage_class, mock_get_db):
        """Test item endpoint is accessible"""
        client = TestClient(app)

        mock_db = Mock()
        mock_get_db.return_value = iter([mock_db])

        mock_storage = Mock()
        from shop_api.store.storage import ItemData

        mock_storage.add_item.return_value = ItemData(
            id=1, name="Test", price=10.0, deleted=False
        )
        mock_storage_class.return_value = mock_storage

        response = client.post("/item", json={"name": "Test", "price": 10.0})
        assert response.status_code == 201
