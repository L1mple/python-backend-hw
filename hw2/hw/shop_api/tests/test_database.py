import pytest
import sys
import os
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shop_api.database import Base, get_db, engine


class TestDatabaseConnection:
    
    def test_database_connection(self):
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    def test_get_db_generator(self):
        db_gen = get_db()
        db = next(db_gen)
        
        assert db is not None
        
        try:
            next(db_gen)
        except StopIteration:
            pass
    
    def test_base_metadata(self):
        table_names = Base.metadata.tables.keys()
        
        assert "users" in table_names
        assert "products" in table_names
        assert "orders" in table_names


class TestDatabaseModels:
    
    def test_user_table_structure(self, db_session):
        from shop_api.database.models import User
        
        columns = User.__table__.columns.keys()
        assert "id" in columns
        assert "email" in columns
        assert "name" in columns
        assert "age" in columns
        assert "created_at" in columns
    
    def test_product_table_structure(self, db_session):
        from shop_api.database.models import Product
        
        columns = Product.__table__.columns.keys()
        assert "id" in columns
        assert "name" in columns
        assert "price" in columns
        assert "description" in columns
        assert "in_stock" in columns
        assert "created_at" in columns
    
    def test_order_table_structure(self, db_session):
        from shop_api.database.models import Order
        
        columns = Order.__table__.columns.keys()
        assert "id" in columns
        assert "user_id" in columns
        assert "product_id" in columns
        assert "quantity" in columns
        assert "total_price" in columns
        assert "status" in columns
        assert "created_at" in columns
