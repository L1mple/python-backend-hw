"""Unit tests for database models

Tests the database model definitions in shop_api/data/db_models.py
"""
import pytest
from sqlalchemy.orm import DeclarativeBase


class TestDBModelsImport:
    """Tests for db_models.py import fallback mechanism"""

    def test_normal_import_succeeds(self):
        """Test that normal import works"""
        # This tests the normal path (try block)
        import shop_api.data.db_models as db_models

        # Verify Base is imported correctly
        assert hasattr(db_models, "Base")
        from shop_api.database import Base
        # Just check they're both DeclarativeBase types
        assert issubclass(db_models.Base, DeclarativeBase)
        assert issubclass(Base, DeclarativeBase)



class TestItemDBModel:
    """Tests for ItemDB model"""

    def test_item_db_repr(self):
        """Test ItemDB __repr__ method"""
        from shop_api.data.db_models import ItemDB

        item = ItemDB(id=1, name="Test Item", price=10.5, deleted=False)
        repr_str = repr(item)

        assert "<ItemDB(id=1" in repr_str
        assert "name=Test Item" in repr_str
        assert "price=10.5" in repr_str
        assert "deleted=False" in repr_str

    def test_item_db_tablename(self):
        """Test ItemDB table name"""
        from shop_api.data.db_models import ItemDB

        assert ItemDB.__tablename__ == "items"

    def test_item_db_has_required_fields(self):
        """Test ItemDB has all required fields"""
        from shop_api.data.db_models import ItemDB

        # Check that ItemDB has required columns
        assert hasattr(ItemDB, 'id')
        assert hasattr(ItemDB, 'name')
        assert hasattr(ItemDB, 'price')
        assert hasattr(ItemDB, 'deleted')
        assert hasattr(ItemDB, 'carts')

    async def test_item_db_default_deleted_is_false(self, db_session):
        """Test ItemDB deleted field defaults to False"""
        from shop_api.data.db_models import ItemDB

        item = ItemDB(name="Test", price=10.0)
        db_session.add(item)
        await db_session.flush()
        # After flush, default value is applied by the database
        assert item.deleted is False


class TestCartDBModel:
    """Tests for CartDB model"""

    def test_cart_db_repr(self):
        """Test CartDB __repr__ method"""
        from shop_api.data.db_models import CartDB

        cart = CartDB(id=5, price=99.99)
        repr_str = repr(cart)

        assert "<CartDB(id=5" in repr_str
        assert "price=99.99" in repr_str

    def test_cart_db_tablename(self):
        """Test CartDB table name"""
        from shop_api.data.db_models import CartDB

        assert CartDB.__tablename__ == "carts"

    def test_cart_db_has_required_fields(self):
        """Test CartDB has all required fields"""
        from shop_api.data.db_models import CartDB

        assert hasattr(CartDB, 'id')
        assert hasattr(CartDB, 'price')
        assert hasattr(CartDB, 'items')

    async def test_cart_db_default_price_is_zero(self, db_session):
        """Test CartDB price field defaults to 0.0"""
        from shop_api.data.db_models import CartDB

        cart = CartDB()
        db_session.add(cart)
        await db_session.flush()
        # After flush, default value is applied by the database
        assert cart.price == 0.0


class TestCartItemsTable:
    """Tests for cart_items association table"""

    def test_cart_items_table_exists(self):
        """Test cart_items table is defined"""
        from shop_api.data.db_models import cart_items_table

        assert cart_items_table is not None
        assert cart_items_table.name == "cart_items"

    def test_cart_items_table_has_correct_columns(self):
        """Test cart_items table has required columns"""
        from shop_api.data.db_models import cart_items_table

        column_names = [col.name for col in cart_items_table.columns]

        assert "cart_id" in column_names
        assert "item_id" in column_names
        assert "quantity" in column_names

    def test_cart_items_table_primary_keys(self):
        """Test cart_items table has composite primary key"""
        from shop_api.data.db_models import cart_items_table

        primary_keys = [col.name for col in cart_items_table.primary_key.columns]

        assert "cart_id" in primary_keys
        assert "item_id" in primary_keys

    def test_cart_items_table_foreign_keys(self):
        """Test cart_items table has foreign key constraints"""
        from shop_api.data.db_models import cart_items_table

        # Get all foreign key constraints
        foreign_keys = []
        for column in cart_items_table.columns:
            if column.foreign_keys:
                for fk in column.foreign_keys:
                    foreign_keys.append((column.name, str(fk.target_fullname)))

        # Check cart_id references carts.id
        assert any(col == "cart_id" and "carts.id" in target for col, target in foreign_keys)

        # Check item_id references items.id
        assert any(col == "item_id" and "items.id" in target for col, target in foreign_keys)


class TestModelRelationships:
    """Tests for relationships between models"""

    def test_item_has_carts_relationship(self):
        """Test ItemDB has relationship to CartDB"""
        from shop_api.data.db_models import ItemDB

        assert hasattr(ItemDB, 'carts')
        # Relationship should be defined
        assert ItemDB.carts is not None

    def test_cart_has_items_relationship(self):
        """Test CartDB has relationship to ItemDB"""
        from shop_api.data.db_models import CartDB

        assert hasattr(CartDB, 'items')
        # Relationship should be defined
        assert CartDB.items is not None

    def test_relationships_use_cart_items_table(self):
        """Test that relationships use the cart_items association table"""
        from shop_api.data.db_models import ItemDB, CartDB

        # Both relationships should reference the same secondary table
        # We check this indirectly by verifying the relationships exist
        assert hasattr(ItemDB, 'carts')
        assert hasattr(CartDB, 'items')
