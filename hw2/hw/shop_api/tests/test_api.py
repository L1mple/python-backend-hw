import pytest
from decimal import Decimal
    
    def test_create_user(self, client):
        response = client.post(
            "/users/",
            json={
                "email": "api@example.com",
                "name": "API User",
                "age": 30
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "api@example.com"
        assert data["name"] == "API User"
        assert data["age"] == 30
        assert "id" in data
        assert "created_at" in data
    
    def test_create_user_invalid_age(self, client):
        response = client.post(
            "/users/",
            json={
                "email": "invalid@example.com",
                "name": "Invalid User",
                "age": -5
            }
        )
        
        assert response.status_code == 422
    
    def test_create_user_duplicate_email(self, client, sample_user):
        response = client.post(
            "/users/",
            json={
                "email": sample_user.email,
                "name": "Duplicate",
                "age": 25
            }
        )
        
        assert response.status_code == 400
    
    def test_get_users(self, client, sample_user):
        response = client.get("/users/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_get_user(self, client, sample_user):
        response = client.get(f"/users/{sample_user.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_user.id
        assert data["email"] == sample_user.email
    
    def test_get_user_not_found(self, client):
        response = client.get("/users/99999")
        
        assert response.status_code == 404
    
    def test_delete_user(self, client, sample_user):
        response = client.delete(f"/users/{sample_user.id}")
        
        assert response.status_code == 200
        
        response = client.get(f"/users/{sample_user.id}")
        assert response.status_code == 404
    
    def test_delete_user_not_found(self, client):
        response = client.delete("/users/99999")
        
        assert response.status_code == 404


class TestProductAPI:
    
    def test_create_product(self, client):
        response = client.post(
            "/products/",
            json={
                "name": "API Product",
                "price": 149.99,
                "description": "API test product",
                "in_stock": True
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Product"
        assert float(data["price"]) == 149.99
        assert data["in_stock"] is True
        assert "id" in data
    
    def test_create_product_invalid_price(self, client):
        response = client.post(
            "/products/",
            json={
                "name": "Invalid Product",
                "price": -10.00,
                "description": "Invalid"
            }
        )
        
        assert response.status_code == 422
    
    def test_get_products(self, client, sample_product):
        response = client.get("/products/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_get_product(self, client, sample_product):
        response = client.get(f"/products/{sample_product.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_product.id
        assert data["name"] == sample_product.name
    
    def test_get_product_not_found(self, client):
        response = client.get("/products/99999")
        
        assert response.status_code == 404


class TestOrderAPI:
    
    def test_create_order(self, client, sample_user, sample_product):
        response = client.post(
            "/orders/",
            json={
                "user_id": sample_user.id,
                "product_id": sample_product.id,
                "quantity": 3
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == sample_user.id
        assert data["product_id"] == sample_product.id
        assert data["quantity"] == 3
        assert data["status"] == "pending"
        assert "id" in data
        assert "total_price" in data
    
    def test_create_order_invalid_quantity(self, client, sample_user, sample_product):
        response = client.post(
            "/orders/",
            json={
                "user_id": sample_user.id,
                "product_id": sample_product.id,
                "quantity": 0
            }
        )
        
        assert response.status_code == 422
    
    def test_create_order_invalid_user(self, client, sample_product):
        response = client.post(
            "/orders/",
            json={
                "user_id": 99999,
                "product_id": sample_product.id,
                "quantity": 1
            }
        )
        
        assert response.status_code == 400
    
    def test_create_order_invalid_product(self, client, sample_user):
        response = client.post(
            "/orders/",
            json={
                "user_id": sample_user.id,
                "product_id": 99999,
                "quantity": 1
            }
        )
        
        assert response.status_code == 400
    
    def test_get_orders(self, client, sample_order):
        response = client.get("/orders/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_get_order(self, client, sample_order):
        response = client.get(f"/orders/{sample_order.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_order.id
        assert data["user_id"] == sample_order.user_id
    
    def test_get_order_not_found(self, client):
        response = client.get("/orders/99999")
        
        assert response.status_code == 404
    
    def test_update_order_status(self, client, sample_order):
        response = client.patch(
            f"/orders/{sample_order.id}/status",
            json={"status": "shipped"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shipped"
    
    def test_update_order_status_invalid(self, client, sample_order):
        response = client.patch(
            f"/orders/{sample_order.id}/status",
            json={"status": "invalid_status"}
        )
        
        assert response.status_code == 422


class TestHealthEndpoints:
    
    def test_metrics_endpoint(self, client):
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "http_requests_total" in response.text
    
    def test_docs_endpoint(self, client):
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "swagger" in response.text.lower()
    
    def test_openapi_endpoint(self, client):
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


class TestCartAPI:
    
    def test_get_cart_empty(self, client):
        response = client.get("/cart")
        
        assert response.status_code == 200
    
    def test_post_cart(self, client):
        response = client.post(
            "/cart",
            json={
                "user_id": 1,
                "items": [{"item_id": 1, "quantity": 2}]
            }
        )
        
        assert response.status_code in [200, 201, 204]


class TestItemAPI:
    
    def test_get_items(self, client):
        response = client.get("/item/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
