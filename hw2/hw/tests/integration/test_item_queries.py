"""Integration tests for item queries

Tests the item database operations in shop_api/data/item_queries.py
These tests use a real database session to verify queries work correctly.
"""
from sqlalchemy import select

from shop_api.data.db_models import ItemDB
from shop_api.data.models import ItemInfo, PatchItemInfo
from shop_api.data import item_queries


class TestItemQueriesAdd:
    """Tests for item_queries.add function"""

    async def test_add_creates_item(self, db_session):
        """Test creating new item"""
        info = ItemInfo(name="Book", price=10.0, deleted=False)
        item = await item_queries.add(db_session, info)

        assert item.id is not None
        assert item.info.name == "Book"
        assert item.info.price == 10.0
        assert item.info.deleted is False

        # Verify in database
        result = await db_session.execute(
            select(ItemDB).where(ItemDB.id == item.id)
        )
        db_item = result.scalar_one()
        assert db_item.name == "Book"
        assert db_item.price == 10.0

    async def test_add_creates_item_with_deleted_flag(self, db_session):
        """Test creating item with deleted=True"""
        info = ItemInfo(name="OldItem", price=5.0, deleted=True)
        item = await item_queries.add(db_session, info)

        assert item.info.deleted is True


class TestItemQueriesGetOne:
    """Tests for item_queries.get_one function"""

    async def test_get_one_returns_correct_item(self, db_session):
        """Test getting existing item by ID"""
        db_session.add(ItemDB(id=1, name="Pen", price=2.5, deleted=False))
        await db_session.flush()

        item = await item_queries.get_one(db_session, 1)

        assert item is not None
        assert item.id == 1
        assert item.info.name == "Pen"
        assert item.info.price == 2.5
        assert not item.info.deleted

    async def test_get_one_returns_none_if_not_found(self, db_session):
        """Test getting non-existent item returns None"""
        item = await item_queries.get_one(db_session, 999)
        assert item is None

    async def test_get_one_returns_deleted_item(self, db_session):
        """Test getting deleted item (it's still returned by get_one)"""
        db_session.add(ItemDB(id=1, name="Deleted", price=1.0, deleted=True))
        await db_session.flush()

        item = await item_queries.get_one(db_session, 1)
        assert item is not None
        assert item.info.deleted is True


class TestItemQueriesGetMany:
    """Tests for item_queries.get_many function"""

    async def test_get_many_returns_empty_list(self, db_session):
        """Test getting items from empty database"""
        items = await item_queries.get_many(db_session)
        assert items == []

    async def test_get_many_returns_all_non_deleted_items(self, db_session):
        """Test getting all non-deleted items"""
        db_session.add_all([
            ItemDB(name="Item1", price=10.0, deleted=False),
            ItemDB(name="Item2", price=20.0, deleted=False),
            ItemDB(name="Deleted", price=5.0, deleted=True),
        ])
        await db_session.flush()

        items = await item_queries.get_many(db_session)
        assert len(items) == 2
        assert all(not item.info.deleted for item in items)

    async def test_get_many_with_show_deleted(self, db_session):
        """Test getting items including deleted ones"""
        db_session.add_all([
            ItemDB(name="Active", price=10.0, deleted=False),
            ItemDB(name="Deleted", price=5.0, deleted=True),
        ])
        await db_session.flush()

        items = await item_queries.get_many(db_session, show_deleted=True)
        assert len(items) == 2

    async def test_get_many_with_price_filters(self, db_session):
        """Test filtering items by price"""
        db_session.add_all([
            ItemDB(name="Cheap", price=1.0, deleted=False),
            ItemDB(name="Medium", price=50.0, deleted=False),
            ItemDB(name="Expensive", price=100.0, deleted=False),
        ])
        await db_session.flush()

        # Filter by min_price
        items = await item_queries.get_many(db_session, min_price=10.0)
        assert len(items) == 2
        assert all(item.info.price >= 10.0 for item in items)

        # Filter by max_price
        items = await item_queries.get_many(db_session, max_price=60.0)
        assert len(items) == 2
        assert all(item.info.price <= 60.0 for item in items)

        # Filter by range
        items = await item_queries.get_many(db_session, min_price=10.0, max_price=60.0)
        assert len(items) == 1
        assert items[0].info.price == 50.0

    async def test_get_many_with_pagination(self, db_session):
        """Test pagination with offset and limit"""
        # Create 5 items
        for i in range(5):
            db_session.add(ItemDB(name=f"Item{i}", price=float(i * 10), deleted=False))
        await db_session.flush()

        # Get first 2
        items = await item_queries.get_many(db_session, offset=0, limit=2)
        assert len(items) == 2

        # Get next 2
        items = await item_queries.get_many(db_session, offset=2, limit=2)
        assert len(items) == 2

        # Get with large offset
        items = await item_queries.get_many(db_session, offset=10, limit=10)
        assert len(items) == 0

    async def test_get_many_excludes_deleted_by_default(self, db_session):
        """Test that deleted items are excluded by default"""
        db_session.add_all([
            ItemDB(name="Active1", price=10.0, deleted=False),
            ItemDB(name="Active2", price=20.0, deleted=False),
            ItemDB(name="Deleted1", price=5.0, deleted=True),
            ItemDB(name="Deleted2", price=15.0, deleted=True),
        ])
        await db_session.flush()

        items = await item_queries.get_many(db_session, show_deleted=False)
        assert len(items) == 2


class TestItemQueriesDelete:
    """Tests for item_queries.delete function"""

    async def test_delete_marks_item_as_deleted(self, db_session):
        """Test soft delete marks item as deleted"""
        db_session.add(ItemDB(id=1, name="Toy", price=5.0, deleted=False))
        await db_session.flush()

        deleted_item = await item_queries.delete(db_session, 1)

        assert deleted_item is not None
        assert deleted_item.info.deleted is True

        # Verify in database
        result = await db_session.execute(select(ItemDB).where(ItemDB.id == 1))
        db_item = result.scalar_one()
        assert db_item.deleted is True

    async def test_delete_returns_none_if_not_found(self, db_session):
        """Test deleting non-existent item returns None"""
        result = await item_queries.delete(db_session, 999)
        assert result is None

    async def test_delete_already_deleted_item(self, db_session):
        """Test deleting already deleted item"""
        db_session.add(ItemDB(id=1, name="AlreadyDeleted", price=10.0, deleted=True))
        await db_session.flush()

        result = await item_queries.delete(db_session, 1)
        assert result is not None
        assert result.info.deleted is True


class TestItemQueriesUpdate:
    """Tests for item_queries.update function"""

    async def test_update_modifies_existing_item(self, db_session):
        """Test updating existing item"""
        db_session.add(ItemDB(id=1, name="Pen", price=2.0, deleted=False))
        await db_session.flush()

        info = ItemInfo(name="Pencil", price=3.0, deleted=False)
        updated = await item_queries.update(db_session, 1, info)

        assert updated is not None
        assert updated.info.name == "Pencil"
        assert updated.info.price == 3.0

        # Verify in database
        result = await db_session.execute(select(ItemDB).where(ItemDB.id == 1))
        db_item = result.scalar_one()
        assert db_item.name == "Pencil"
        assert db_item.price == 3.0

    async def test_update_returns_none_if_not_exists(self, db_session):
        """Test updating non-existent item returns None"""
        info = ItemInfo(name="Ghost", price=9.99, deleted=False)
        result = await item_queries.update(db_session, 999, info)
        assert result is None

    async def test_update_can_change_deleted_flag(self, db_session):
        """Test update can change deleted flag"""
        db_session.add(ItemDB(id=1, name="Item", price=10.0, deleted=False))
        await db_session.flush()

        info = ItemInfo(name="Item", price=10.0, deleted=True)
        updated = await item_queries.update(db_session, 1, info)

        assert updated.info.deleted is True


class TestItemQueriesUpsert:
    """Tests for item_queries.upsert function"""

    async def test_upsert_creates_if_not_exists(self, db_session):
        """Test upsert creates new item if it doesn't exist"""
        info = ItemInfo(name="Apple", price=1.5, deleted=False)
        created = await item_queries.upsert(db_session, 100, info)

        assert created.id == 100
        assert created.info.name == "Apple"
        assert created.info.price == 1.5

        # Verify in database
        result = await db_session.execute(select(ItemDB).where(ItemDB.id == 100))
        db_item = result.scalar_one()
        assert db_item.name == "Apple"

    async def test_upsert_updates_if_exists(self, db_session):
        """Test upsert updates existing item"""
        db_session.add(ItemDB(id=1, name="Apple", price=1.5, deleted=False))
        await db_session.flush()

        updated_info = ItemInfo(name="Green Apple", price=2.0, deleted=False)
        updated = await item_queries.upsert(db_session, 1, updated_info)

        assert updated.id == 1
        assert updated.info.name == "Green Apple"
        assert updated.info.price == 2.0

        # Verify in database
        result = await db_session.execute(select(ItemDB).where(ItemDB.id == 1))
        db_item = result.scalar_one()
        assert db_item.name == "Green Apple"
        assert db_item.price == 2.0

    async def test_upsert_with_specific_id(self, db_session):
        """Test upsert with specific ID"""
        info = ItemInfo(name="SpecificID", price=50.0, deleted=False)
        item = await item_queries.upsert(db_session, 42, info)

        assert item.id == 42


class TestItemQueriesPatch:
    """Tests for item_queries.patch function"""

    async def test_patch_updates_partial_fields_name_only(self, db_session):
        """Test patching only name field"""
        db_session.add(ItemDB(id=1, name="Table", price=50.0, deleted=False))
        await db_session.flush()

        patch_info = PatchItemInfo(name="Desk", price=None, deleted=None)
        patched = await item_queries.patch(db_session, 1, patch_info)

        assert patched is not None
        assert patched.info.name == "Desk"
        assert patched.info.price == 50.0  # Unchanged

    async def test_patch_updates_partial_fields_price_only(self, db_session):
        """Test patching only price field"""
        db_session.add(ItemDB(id=1, name="Chair", price=30.0, deleted=False))
        await db_session.flush()

        patch_info = PatchItemInfo(name=None, price=40.0, deleted=None)
        patched = await item_queries.patch(db_session, 1, patch_info)

        assert patched is not None
        assert patched.info.name == "Chair"  # Unchanged
        assert patched.info.price == 40.0

    async def test_patch_updates_multiple_fields(self, db_session):
        """Test patching multiple fields"""
        db_session.add(ItemDB(id=1, name="Old", price=10.0, deleted=False))
        await db_session.flush()

        patch_info = PatchItemInfo(name="New", price=20.0, deleted=None)
        patched = await item_queries.patch(db_session, 1, patch_info)

        assert patched.info.name == "New"
        assert patched.info.price == 20.0

    async def test_patch_returns_none_if_item_not_found(self, db_session):
        """Test patching non-existent item returns None"""
        patch_info = PatchItemInfo(name="Ghost", price=None, deleted=None)
        result = await item_queries.patch(db_session, 999, patch_info)
        assert result is None

    async def test_patch_with_empty_fields(self, db_session):
        """Test patching with all None fields (no change)"""
        db_session.add(ItemDB(id=1, name="Unchanged", price=15.0, deleted=False))
        await db_session.flush()

        patch_info = PatchItemInfo(name=None, price=None, deleted=None)
        patched = await item_queries.patch(db_session, 1, patch_info)

        assert patched.info.name == "Unchanged"
        assert patched.info.price == 15.0

    async def test_patch_can_change_deleted_flag(self, db_session):
        """Test patch can change deleted flag"""
        db_session.add(ItemDB(id=1, name="Item", price=10.0, deleted=False))
        await db_session.flush()

        patch_info = PatchItemInfo(name=None, price=None, deleted=True)
        patched = await item_queries.patch(db_session, 1, patch_info)

        assert patched.info.deleted is True


class TestItemQueriesEdgeCases:
    """Tests for edge cases and boundary conditions"""

    async def test_add_item_with_zero_price(self, db_session):
        """Test creating item with zero price"""
        info = ItemInfo(name="Free", price=0.0, deleted=False)
        item = await item_queries.add(db_session, info)

        assert item.info.price == 0.0

    async def test_add_item_with_very_large_price(self, db_session):
        """Test creating item with very large price"""
        info = ItemInfo(name="Expensive", price=999999.99, deleted=False)
        item = await item_queries.add(db_session, info)

        assert item.info.price == 999999.99

    async def test_get_many_with_zero_offset_and_limit(self, db_session):
        """Test pagination with offset=0 and small limit"""
        db_session.add_all([
            ItemDB(name="Item1", price=10.0, deleted=False),
            ItemDB(name="Item2", price=20.0, deleted=False),
            ItemDB(name="Item3", price=30.0, deleted=False),
        ])
        await db_session.flush()

        items = await item_queries.get_many(db_session, offset=0, limit=1)
        assert len(items) == 1

    async def test_get_many_with_equal_min_max_price(self, db_session):
        """Test filtering with min_price = max_price"""
        db_session.add_all([
            ItemDB(name="Exact", price=50.0, deleted=False),
            ItemDB(name="Higher", price=60.0, deleted=False),
            ItemDB(name="Lower", price=40.0, deleted=False),
        ])
        await db_session.flush()

        items = await item_queries.get_many(db_session, min_price=50.0, max_price=50.0)
        assert len(items) == 1
        assert items[0].info.price == 50.0

    async def test_update_deleted_item(self, db_session):
        """Test updating a deleted item is possible"""
        db_session.add(ItemDB(id=1, name="Deleted", price=10.0, deleted=True))
        await db_session.flush()

        info = ItemInfo(name="Restored", price=15.0, deleted=False)
        updated = await item_queries.update(db_session, 1, info)

        assert updated is not None
        assert updated.info.deleted is False
        assert updated.info.name == "Restored"
