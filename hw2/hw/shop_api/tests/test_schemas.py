import pytest
import sys
import os
from decimal import Decimal
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shop_api.database.schemas import (
    UserCreate, UserResponse,
    ProductCreate, ProductResponse,
    OrderCreate, OrderResponse
)


class TestUserSchemas:
    
    def test_user_create_valid(self):
        user = UserCreate(
            email="test@example.com",
            name="Test User",
            age=25
        )
        
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.age == 25
    
    def test_user_create_invalid_email(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="invalid-email",
                name="Test",
                age=25
            )
    
    def test_user_create_negative_age(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                name="Test",
                age=-1
            )
    
    def test_user_response(self):
        from datetime import datetime
        
        user = UserResponse(
            id=1,
            email="test@example.com",
            name="Test User",
            age=25,
            created_at=datetime.now()
        )
        
        assert user.id == 1
        assert user.email == "test@example.com"


class TestProductSchemas:
    
    def test_product_create_valid(self):
        product = ProductCreate(
            name="Test Product",
            price=Decimal("99.99"),
            description="Test description",
            in_stock=True
        )
        
        assert product.name == "Test Product"
        assert product.price == Decimal("99.99")
        assert product.in_stock is True
    
    def test_product_create_negative_price(self):
        with pytest.raises(ValidationError):
            ProductCreate(
                name="Test",
                price=Decimal("-10.00"),
                description="Test"
            )
    
    def test_product_create_defaults(self):
        product = ProductCreate(
            name="Test Product",
            price=Decimal("99.99")
        )
        
        assert product.in_stock is True
        assert product.description is None
    
    def test_product_response(self):
        from datetime import datetime
        
        product = ProductResponse(
            id=1,
            name="Test Product",
            price=Decimal("99.99"),
            description="Test",
            in_stock=True,
            created_at=datetime.now()
        )
        
        assert product.id == 1
        assert product.name == "Test Product"


class TestOrderSchemas:
    
    def test_order_create_valid(self):
        order = OrderCreate(
            user_id=1,
            product_id=1,
            quantity=2
        )
        
        assert order.user_id == 1
        assert order.product_id == 1
        assert order.quantity == 2
    
    def test_order_create_invalid_quantity(self):
        with pytest.raises(ValidationError):
            OrderCreate(
                user_id=1,
                product_id=1,
                quantity=0
            )
    
    def test_order_response(self):
        from datetime import datetime
        
        order = OrderResponse(
            id=1,
            user_id=1,
            product_id=1,
            quantity=2,
            total_price=Decimal("199.98"),
            status="pending",
            created_at=datetime.now()
        )
        
        assert order.id == 1
        assert order.quantity == 2
        assert order.status == "pending"
