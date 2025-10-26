"""Tests for shop_api.database module"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from shop_api.database import ItemDB, CartDB, CartItemDB, init_db, get_db


class TestDatabaseModels:
    """Test database models structure"""

    def test_item_db_attributes(self):
        """Test ItemDB has correct attributes"""
        assert hasattr(ItemDB, "__tablename__")
        assert ItemDB.__tablename__ == "items"
        assert hasattr(ItemDB, "id")
        assert hasattr(ItemDB, "name")
        assert hasattr(ItemDB, "price")
        assert hasattr(ItemDB, "deleted")

    def test_cart_db_attributes(self):
        """Test CartDB has correct attributes"""
        assert hasattr(CartDB, "__tablename__")
        assert CartDB.__tablename__ == "carts"
        assert hasattr(CartDB, "id")
        assert hasattr(CartDB, "price")
        assert hasattr(CartDB, "cart_items")

    def test_cart_item_db_attributes(self):
        """Test CartItemDB has correct attributes"""
        assert hasattr(CartItemDB, "__tablename__")
        assert CartItemDB.__tablename__ == "cart_items"
        assert hasattr(CartItemDB, "id")
        assert hasattr(CartItemDB, "cart_id")
        assert hasattr(CartItemDB, "item_id")
        assert hasattr(CartItemDB, "quantity")
        assert hasattr(CartItemDB, "cart")
        assert hasattr(CartItemDB, "item")


class TestInitDb:
    """Test init_db function"""

    @patch("shop_api.database.Base")
    def test_init_db_creates_tables(self, mock_base):
        """Test init_db calls create_all"""
        mock_metadata = Mock()
        mock_base.metadata = mock_metadata

        init_db()

        mock_metadata.create_all.assert_called_once()


class TestGetDb:
    """Test get_db generator"""

    @patch("shop_api.database.SessionLocal")
    def test_get_db_yields_session(self, mock_session_local):
        """Test get_db yields database session"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db

        gen = get_db()
        db = next(gen)

        assert db == mock_db
        mock_session_local.assert_called_once()

    @patch("shop_api.database.SessionLocal")
    def test_get_db_closes_session(self, mock_session_local):
        """Test get_db closes session after use"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db

        gen = get_db()
        next(gen)

        try:
            next(gen)
        except StopIteration:
            pass

        mock_db.close.assert_called_once()

    @patch("shop_api.database.SessionLocal")
    def test_get_db_closes_on_exception(self, mock_session_local):
        """Test get_db closes session even on exception"""
        mock_db = Mock()
        mock_session_local.return_value = mock_db

        gen = get_db()
        next(gen)

        try:
            gen.throw(Exception("Test exception"))
        except Exception:
            pass

        mock_db.close.assert_called_once()
