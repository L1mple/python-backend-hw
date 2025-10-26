import pytest
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shop_api.database.crud import (
    create_user, get_user, get_users, delete_user,
    create_product, get_product, get_products,
    create_order, get_order, get_orders, update_order_status
)
from shop_api.database.schemas import UserCreate, ProductCreate, OrderCreate


class TestUserCRUD:
    
    def test_create_user(self, db_session):
        user_data = UserCreate(
            email="crud@example.com",
            name="CRUD User",
            age=28
        )
        user = create_user(db_session, user_data)
        
        assert user.id is not None
        assert user.email == "crud@example.com"
        assert user.name == "CRUD User"
        assert user.age == 28
    
    def test_get_user(self, db_session, sample_user):
        user = get_user(db_session, sample_user.id)
        
        assert user is not None
        assert user.id == sample_user.id
        assert user.email == sample_user.email
    
    def test_get_user_not_found(self, db_session):
        user = get_user(db_session, 99999)
        assert user is None
    
    def test_get_users(self, db_session, sample_user):
        users = get_users(db_session)
        
        assert len(users) >= 1
        assert any(u.id == sample_user.id for u in users)
    
    def test_get_users_with_limit(self, db_session):
        for i in range(5):
            user_data = UserCreate(
                email=f"user{i}@example.com",
                name=f"User {i}",
                age=20 + i
            )
            create_user(db_session, user_data)
        
        users = get_users(db_session, skip=0, limit=3)
        assert len(users) == 3
    
    def test_delete_user(self, db_session, sample_user):
        user_id = sample_user.id
        deleted = delete_user(db_session, user_id)
        
        assert deleted is True
        assert get_user(db_session, user_id) is None
    
    def test_delete_user_not_found(self, db_session):
        deleted = delete_user(db_session, 99999)
        assert deleted is False


class TestProductCRUD:
    
    def test_create_product(self, db_session):
        product_data = ProductCreate(
            name="CRUD Product",
            price=Decimal("79.99"),
            description="CRUD test product",
            in_stock=True
        )
        product = create_product(db_session, product_data)
        
        assert product.id is not None
        assert product.name == "CRUD Product"
        assert product.price == Decimal("79.99")
        assert product.in_stock is True
    
    def test_get_product(self, db_session, sample_product):
        product = get_product(db_session, sample_product.id)
        
        assert product is not None
        assert product.id == sample_product.id
        assert product.name == sample_product.name
    
    def test_get_product_not_found(self, db_session):
        product = get_product(db_session, 99999)
        assert product is None
    
    def test_get_products(self, db_session, sample_product):
        products = get_products(db_session)
        
        assert len(products) >= 1
        assert any(p.id == sample_product.id for p in products)
    
    def test_get_products_with_limit(self, db_session):
        for i in range(5):
            product_data = ProductCreate(
                name=f"Product {i}",
                price=Decimal(f"{10 + i}.99"),
                description=f"Product {i} description"
            )
            create_product(db_session, product_data)
        
        products = get_products(db_session, skip=0, limit=3)
        assert len(products) == 3


class TestOrderCRUD:
    
    def test_create_order(self, db_session, sample_user, sample_product):
        order_data = OrderCreate(
            user_id=sample_user.id,
            product_id=sample_product.id,
            quantity=2
        )
        order = create_order(db_session, order_data)
        
        assert order.id is not None
        assert order.user_id == sample_user.id
        assert order.product_id == sample_product.id
        assert order.quantity == 2
        assert order.total_price == sample_product.price * 2
        assert order.status == "pending"
    
    def test_get_order(self, db_session, sample_order):
        order = get_order(db_session, sample_order.id)
        
        assert order is not None
        assert order.id == sample_order.id
        assert order.user_id == sample_order.user_id
    
    def test_get_order_not_found(self, db_session):
        order = get_order(db_session, 99999)
        assert order is None
    
    def test_get_orders(self, db_session, sample_order):
        orders = get_orders(db_session)
        
        assert len(orders) >= 1
        assert any(o.id == sample_order.id for o in orders)
    
    def test_get_orders_with_limit(self, db_session, sample_user, sample_product):
        for i in range(5):
            order_data = OrderCreate(
                user_id=sample_user.id,
                product_id=sample_product.id,
                quantity=i + 1
            )
            create_order(db_session, order_data)
        
        orders = get_orders(db_session, skip=0, limit=3)
        assert len(orders) == 3
    
    def test_update_order_status(self, db_session, sample_order):
        updated_order = update_order_status(
            db_session,
            sample_order.id,
            "shipped"
        )
        
        assert updated_order is not None
        assert updated_order.status == "shipped"
    
    def test_update_order_status_not_found(self, db_session):
        updated_order = update_order_status(db_session, 99999, "shipped")
        assert updated_order is None
    
    def test_create_order_calculates_total(self, db_session, sample_user, sample_product):
        quantity = 5
        order_data = OrderCreate(
            user_id=sample_user.id,
            product_id=sample_product.id,
            quantity=quantity
        )
        order = create_order(db_session, order_data)
        
        expected_total = sample_product.price * quantity
        assert order.total_price == expected_total
