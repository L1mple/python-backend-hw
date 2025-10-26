import pytest
import sys
import os
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shop_api.database.models import User, Product, Order


class TestUserModel:
    
    def test_create_user(self, db_session):
        user = User(email="new@example.com", name="New User", age=30)
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email == "new@example.com"
        assert user.name == "New User"
        assert user.age == 30
        assert user.created_at is not None
    
    def test_user_email_unique(self, db_session, sample_user):
        duplicate_user = User(
            email=sample_user.email,
            name="Duplicate",
            age=25
        )
        db_session.add(duplicate_user)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_user_age_constraint(self, db_session):
        user = User(email="test@test.com", name="Test", age=-1)
        db_session.add(user)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_user_relationships(self, db_session, sample_user, sample_product):
        order = Order(
            user_id=sample_user.id,
            product_id=sample_product.id,
            quantity=1,
            total_price=99.99
        )
        db_session.add(order)
        db_session.commit()
        
        db_session.refresh(sample_user)
        assert len(sample_user.orders) == 1
        assert sample_user.orders[0].id == order.id


class TestProductModel:
    
    def test_create_product(self, db_session):
        product = Product(
            name="New Product",
            price=Decimal("49.99"),
            description="Test product",
            in_stock=True
        )
        db_session.add(product)
        db_session.commit()
        
        assert product.id is not None
        assert product.name == "New Product"
        assert product.price == Decimal("49.99")
        assert product.in_stock is True
        assert product.created_at is not None
    
    def test_product_price_constraint(self, db_session):
        product = Product(
            name="Invalid Product",
            price=Decimal("-10.00"),
            description="Invalid"
        )
        db_session.add(product)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_product_default_in_stock(self, db_session):
        product = Product(
            name="Default Product",
            price=Decimal("29.99")
        )
        db_session.add(product)
        db_session.commit()
        
        assert product.in_stock is True
    
    def test_product_relationships(self, db_session, sample_user, sample_product):
        order = Order(
            user_id=sample_user.id,
            product_id=sample_product.id,
            quantity=1,
            total_price=99.99
        )
        db_session.add(order)
        db_session.commit()
        
        db_session.refresh(sample_product)
        assert len(sample_product.orders) == 1
        assert sample_product.orders[0].id == order.id


class TestOrderModel:
    
    def test_create_order(self, db_session, sample_user, sample_product):
        order = Order(
            user_id=sample_user.id,
            product_id=sample_product.id,
            quantity=3,
            total_price=Decimal("299.97"),
            status="pending"
        )
        db_session.add(order)
        db_session.commit()
        
        assert order.id is not None
        assert order.user_id == sample_user.id
        assert order.product_id == sample_product.id
        assert order.quantity == 3
        assert order.total_price == Decimal("299.97")
        assert order.status == "pending"
        assert order.created_at is not None
    
    def test_order_quantity_constraint(self, db_session, sample_user, sample_product):
        order = Order(
            user_id=sample_user.id,
            product_id=sample_product.id,
            quantity=0,
            total_price=0
        )
        db_session.add(order)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_order_total_price_constraint(self, db_session, sample_user, sample_product):
        order = Order(
            user_id=sample_user.id,
            product_id=sample_product.id,
            quantity=1,
            total_price=Decimal("-10.00")
        )
        db_session.add(order)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_order_status_constraint(self, db_session, sample_user, sample_product):
        order = Order(
            user_id=sample_user.id,
            product_id=sample_product.id,
            quantity=1,
            total_price=99.99,
            status="invalid_status"
        )
        db_session.add(order)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_order_default_status(self, db_session, sample_user, sample_product):
        order = Order(
            user_id=sample_user.id,
            product_id=sample_product.id,
            quantity=1,
            total_price=99.99
        )
        db_session.add(order)
        db_session.commit()
        
        assert order.status == "pending"
    
    def test_order_relationships(self, db_session, sample_order):
        assert sample_order.user is not None
        assert sample_order.user.email == "test@example.com"
        assert sample_order.product is not None
        assert sample_order.product.name == "Test Product"
