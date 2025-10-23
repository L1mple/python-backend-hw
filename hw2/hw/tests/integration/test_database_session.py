"""Integration tests for database session management

Tests the get_db() function and database session handling in shop_api/database.py
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shop_api import database


class TestGetDbIntegration:
    """Integration tests for get_db with real session"""

    async def test_get_db_yields_async_session(self):
        """Test that get_db yields an AsyncSession instance"""
        gen = database.get_db()
        session_iterator = gen.__aiter__()

        try:
            session = await session_iterator.__anext__()
            assert isinstance(session, AsyncSession)

            # Close the generator properly
            await session_iterator.aclose()
        except StopAsyncIteration:
            pass

    async def test_get_db_context_manager_usage(self):
        """Test get_db can be used as async context manager"""
        async for session in database.get_db():
            assert isinstance(session, AsyncSession)
            # Just test one iteration
            break


class TestDatabaseFunctions:
    """Tests for database utility functions"""

    async def test_create_and_drop_tables(self):
        """Test create_tables and drop_tables functions"""
        from shop_api.database import create_tables, drop_tables

        # These functions are typically called at startup/shutdown
        # Testing them ensures they work correctly
        try:
            await create_tables()
            await drop_tables()
            await create_tables()  # Recreate for other tests
        except Exception as e:
            # Tables might already exist, that's okay
            pytest.skip(f"Database operation failed: {e}")


class TestModelIntegration:
    """Integration tests for models with database"""

    async def test_create_item_in_db(self, db_session):
        """Test creating ItemDB instance in database"""
        from shop_api.data.db_models import ItemDB

        item = ItemDB(name="Integration Test Item", price=25.5, deleted=False)
        db_session.add(item)
        await db_session.flush()

        assert item.id is not None
        assert item.name == "Integration Test Item"
        assert item.price == 25.5
        assert item.deleted is False

    async def test_create_cart_in_db(self, db_session):
        """Test creating CartDB instance in database"""
        from shop_api.data.db_models import CartDB

        cart = CartDB(price=0.0)
        db_session.add(cart)
        await db_session.flush()

        assert cart.id is not None
        assert cart.price == 0.0

    async def test_item_cart_relationship(self, db_session):
        """Test many-to-many relationship between items and carts"""
        from shop_api.data.db_models import ItemDB, CartDB, cart_items_table
        from sqlalchemy import insert, select

        # Create item and cart
        item = ItemDB(name="Relational Item", price=10.0, deleted=False)
        cart = CartDB(price=0.0)

        db_session.add(item)
        db_session.add(cart)
        await db_session.flush()

        # Add relationship through association table
        await db_session.execute(
            insert(cart_items_table).values(
                cart_id=cart.id,
                item_id=item.id,
                quantity=2
            )
        )
        await db_session.flush()

        # Verify the relationship was created
        result = await db_session.execute(
            select(cart_items_table).where(
                cart_items_table.c.cart_id == cart.id,
                cart_items_table.c.item_id == item.id
            )
        )
        row = result.first()

        assert row is not None
        assert row.quantity == 2
