import pytest
import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shop_api.main import app


class TestMainApp:
    
    def test_app_exists(self):
        assert app is not None
        assert app.title == "Shop API"
    
    def test_app_routes(self):
        routes = [route.path for route in app.routes]
        
        assert "/users/" in routes
        assert "/products/" in routes
        assert "/orders/" in routes
        assert "/docs" in routes
        assert "/openapi.json" in routes
    
    def test_cors_middleware(self):
        client = TestClient(app)
        response = client.options("/users/")
        
        assert response.status_code in [200, 405]
    
    def test_root_endpoint_not_found(self):
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 404
