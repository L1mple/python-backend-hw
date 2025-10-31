"""Integration tests for cart queries

Tests the cart database operations in shop_api/data/cart_queries.py
These tests use a real database session to verify queries work correctly.
"""
from shop_api.data.db_models import CartDB, ItemDB
from shop_api.data.models import CartInfo, CartItemInfo, PatchCartInfo
from shop_api.data import cart_queries


class TestCartQueriesAdd:
    """Tests for cart_queries.add function"""

    async def test_add_empty_cart(self, db_session):
        """Test creating empty cart"""
        info = CartInfo(items=[], price=0.0)
        cart = await cart_queries.add(db_session, info)

        assert cart.id is not None
        assert cart.info.price == 0.0
        assert len(cart.info.items) == 0

    async def test_add_cart_with_items(self, db_session):
        """Test creating cart with items and price calculation"""
        # Create items first
        db_session.add_all([
            ItemDB(id=1, name="Apple", price=2.0, deleted=False),
            ItemDB(id=2, name="Banana", price=3.0, deleted=False),
        ])
        await db_session.flush()

        info = CartInfo(
            items=[
                CartItemInfo(id=1, name="Apple", quantity=2, available=True),
                CartItemInfo(id=2, name="Banana", quantity=1, available=True),
            ],
            price=0.0
        )

        cart = await cart_queries.add(db_session, info)

        assert cart.id is not None
        assert cart.info.price == 7.0  # 2*2 + 3*1
        assert len(cart.info.items) == 2

    async def test_add_cart_with_nonexistent_item(self, db_session):
        """Test creating cart with non-existent item (should skip it)"""
        db_session.add(ItemDB(id=1, name="Apple", price=2.0, deleted=False))
        await db_session.flush()

        info = CartInfo(
            items=[
                CartItemInfo(id=1, name="Apple", quantity=1, available=True),
                CartItemInfo(id=999, name="Ghost", quantity=1, available=True),
            ],
            price=0.0
        )

        cart = await cart_queries.add(db_session, info)

        assert len(cart.info.items) == 1  # Only Apple added
        assert cart.info.price == 2.0


class TestCartQueriesGetOne:
    """Tests for cart_queries.get_one function"""

    async def test_get_one_existing_cart(self, db_session):
        """Test getting existing cart"""
        db_session.add(CartDB(id=1, price=10.0))
        await db_session.flush()

        cart = await cart_queries.get_one(db_session, 1)

        assert cart is not None
        assert cart.id == 1

    async def test_get_one_nonexistent_cart(self, db_session):
        """Test getting non-existent cart returns None"""
        cart = await cart_queries.get_one(db_session, 999)
        assert cart is None

    async def test_get_one_with_items(self, db_session):
        """Test getting cart with items"""
        # Create items
        db_session.add_all([
            ItemDB(id=1, name="Pen", price=2.0, deleted=False),
            ItemDB(id=2, name="Pencil", price=1.0, deleted=False),
        ])
        await db_session.flush()

        # Create cart with items
        info = CartInfo(
            items=[
                CartItemInfo(id=1, name="Pen", quantity=2, available=True),
                CartItemInfo(id=2, name="Pencil", quantity=3, available=True),
            ],
            price=0.0
        )
        cart = await cart_queries.add(db_session, info)

        # Get cart
        retrieved = await cart_queries.get_one(db_session, cart.id)

        assert retrieved is not None
        assert len(retrieved.info.items) == 2
        assert retrieved.info.price == 7.0  # 2*2 + 1*3


class TestCartQueriesGetMany:
    """Tests for cart_queries.get_many function"""

    async def test_get_many_empty_database(self, db_session):
        """Test getting carts from empty database"""
        carts = await cart_queries.get_many(db_session)
        assert isinstance(carts, list)

    async def test_get_many_skips_none_cart_entities(self, db_session):
        """Test that get_many continues when get_one returns None (line 100)"""
        # Create a cart directly in DB without proper setup
        # This simulates a corrupted cart that get_one can't load
        from shop_api.data.db_models import CartDB
        from unittest.mock import patch, AsyncMock

        # Add a cart to database
        db_session.add(CartDB(id=999, price=10.0))
        await db_session.flush()

        # Mock get_one to return None for this cart
        original_get_one = cart_queries.get_one

        async def mock_get_one(session, cart_id):
            if cart_id == 999:
                return None  # Simulate corrupted cart
            return await original_get_one(session, cart_id)

        with patch("shop_api.data.cart_queries.get_one", side_effect=mock_get_one):
            carts = await cart_queries.get_many(db_session)
            # Should skip the None cart (line 100: continue)
            assert all(cart is not None for cart in carts)

    async def test_get_many_with_pagination(self, db_session):
        """Test pagination works correctly"""
        # Create 5 carts
        for i in range(5):
            db_session.add(CartDB(price=float(i * 10)))
        await db_session.flush()

        # Get first 2
        carts = await cart_queries.get_many(db_session, offset=0, limit=2)
        assert len(carts) == 2

        # Get next 2
        carts = await cart_queries.get_many(db_session, offset=2, limit=2)
        assert len(carts) == 2

    async def test_get_many_with_price_filter(self, db_session):
        """Test price filtering"""
        db_session.add_all([
            CartDB(price=10.0),
            CartDB(price=50.0),
            CartDB(price=100.0),
        ])
        await db_session.flush()

        # Filter by min_price
        carts = await cart_queries.get_many(db_session, min_price=40.0)
        assert len(carts) == 2
        assert all(cart.info.price >= 40.0 for cart in carts)

        # Filter by max_price
        carts = await cart_queries.get_many(db_session, max_price=60.0)
        assert len(carts) == 2
        assert all(cart.info.price <= 60.0 for cart in carts)

        # Filter by range
        carts = await cart_queries.get_many(db_session, min_price=40.0, max_price=60.0)
        assert len(carts) == 1
        assert carts[0].info.price == 50.0

    async def test_get_many_with_quantity_filter(self, db_session):
        """Test quantity filtering"""
        # Create items
        db_session.add_all([
            ItemDB(id=1, name="Item", price=10.0, deleted=False),
        ])
        await db_session.flush()

        # Create carts with different quantities
        info1 = CartInfo(items=[CartItemInfo(id=1, name="Item", quantity=2, available=True)], price=0.0)
        info2 = CartInfo(items=[CartItemInfo(id=1, name="Item", quantity=5, available=True)], price=0.0)
        info3 = CartInfo(items=[CartItemInfo(id=1, name="Item", quantity=10, available=True)], price=0.0)

        await cart_queries.add(db_session, info1)
        await cart_queries.add(db_session, info2)
        await cart_queries.add(db_session, info3)

        # Filter by min_quantity
        carts = await cart_queries.get_many(db_session, min_quantity=5)
        assert len(carts) == 2
        for cart in carts:
            total = sum(item.quantity for item in cart.info.items)
            assert total >= 5

        # Filter by max_quantity
        carts = await cart_queries.get_many(db_session, max_quantity=5)
        assert len(carts) == 2


class TestCartQueriesUpdate:
    """Tests for cart_queries.update function"""

    async def test_update_existing_cart(self, db_session):
        """Test updating existing cart"""
        # Create items
        db_session.add_all([
            ItemDB(id=1, name="Item1", price=10.0, deleted=False),
            ItemDB(id=2, name="Item2", price=20.0, deleted=False),
        ])
        await db_session.flush()

        # Create cart
        info = CartInfo(items=[CartItemInfo(id=1, name="Item1", quantity=1, available=True)], price=0.0)
        cart = await cart_queries.add(db_session, info)
        assert cart.info.price == 10.0

        # Update cart with different items
        new_info = CartInfo(items=[CartItemInfo(id=2, name="Item2", quantity=2, available=True)], price=0.0)
        updated = await cart_queries.update(db_session, cart.id, new_info)

        assert updated is not None
        assert updated.info.price == 40.0  # 20*2
        assert len(updated.info.items) == 1
        assert updated.info.items[0].id == 2

    async def test_update_nonexistent_cart(self, db_session):
        """Test updating non-existent cart returns None"""
        info = CartInfo(items=[], price=0.0)
        result = await cart_queries.update(db_session, 999, info)
        assert result is None


class TestCartQueriesUpsert:
    """Tests for cart_queries.upsert function"""

    async def test_upsert_creates_new_cart(self, db_session):
        """Test upsert creates new cart when it doesn't exist"""
        db_session.add(ItemDB(id=1, name="Book", price=10.0, deleted=False))
        await db_session.flush()

        info = CartInfo(items=[CartItemInfo(id=1, name="Book", quantity=1, available=True)], price=0.0)
        cart = await cart_queries.upsert(db_session, 100, info)

        assert cart.id == 100
        assert cart.info.price == 10.0

    async def test_upsert_updates_existing_cart(self, db_session):
        """Test upsert updates existing cart"""
        # Create items
        db_session.add_all([
            ItemDB(id=1, name="Book", price=10.0, deleted=False),
            ItemDB(id=2, name="Pen", price=2.0, deleted=False),
        ])
        await db_session.flush()

        # Create initial cart
        info = CartInfo(items=[CartItemInfo(id=1, name="Book", quantity=1, available=True)], price=0.0)
        cart = await cart_queries.upsert(db_session, 1, info)
        assert cart.info.price == 10.0

        # Upsert with new data
        new_info = CartInfo(items=[CartItemInfo(id=1, name="Book", quantity=2, available=True)], price=0.0)
        updated = await cart_queries.upsert(db_session, 1, new_info)
        assert updated.info.price == 20.0


class TestCartQueriesPatch:
    """Tests for cart_queries.patch function"""

    async def test_patch_existing_cart(self, db_session):
        """Test patching existing cart"""
        # Create items
        db_session.add_all([
            ItemDB(id=1, name="Item1", price=10.0, deleted=False),
            ItemDB(id=2, name="Item2", price=20.0, deleted=False),
        ])
        await db_session.flush()

        # Create cart
        info = CartInfo(items=[CartItemInfo(id=1, name="Item1", quantity=1, available=True)], price=0.0)
        cart = await cart_queries.add(db_session, info)

        # Patch with new items
        patch_info = PatchCartInfo(items=[CartItemInfo(id=2, name="Item2", quantity=1, available=True)])
        patched = await cart_queries.patch(db_session, cart.id, patch_info)

        assert patched is not None
        assert patched.info.price == 20.0

    async def test_patch_nonexistent_cart(self, db_session):
        """Test patching non-existent cart returns None"""
        patch_info = PatchCartInfo(items=[])
        result = await cart_queries.patch(db_session, 999, patch_info)
        assert result is None

    async def test_patch_with_none_items(self, db_session):
        """Test patching cart with None items (no change)"""
        # Create cart
        db_session.add(CartDB(id=1, price=50.0))
        await db_session.flush()

        # Patch with None items
        patch_info = PatchCartInfo(items=None)
        patched = await cart_queries.patch(db_session, 1, patch_info)

        assert patched is not None
        assert patched.info.price == 50.0  # Price unchanged


class TestCartQueriesDelete:
    """Tests for cart_queries.delete function"""

    async def test_delete_existing_cart(self, db_session):
        """Test deleting existing cart"""
        db_session.add(CartDB(id=1, price=10.0))
        await db_session.flush()

        await cart_queries.delete(db_session, 1)

        # Verify cart is deleted
        cart = await cart_queries.get_one(db_session, 1)
        assert cart is None

    async def test_delete_nonexistent_cart(self, db_session):
        """Test deleting non-existent cart (should not raise error)"""
        await cart_queries.delete(db_session, 999)
        # Should complete without error


class TestCartQueriesAddItemToCart:
    """Tests for cart_queries.add_item_to_cart function"""

    async def test_add_item_to_empty_cart(self, db_session):
        """Test adding item to empty cart"""
        db_session.add_all([
            CartDB(id=1, price=0.0),
            ItemDB(id=1, name="Pen", price=2.0, deleted=False),
        ])
        await db_session.flush()

        cart = await cart_queries.add_item_to_cart(db_session, 1, 1, 3)

        assert cart is not None
        assert len(cart.info.items) == 1
        assert cart.info.items[0].quantity == 3
        assert cart.info.price == 6.0

    async def test_add_item_increases_quantity(self, db_session):
        """Test adding item that already exists increases quantity"""
        db_session.add_all([
            CartDB(id=1, price=0.0),
            ItemDB(id=1, name="Pen", price=2.0, deleted=False),
        ])
        await db_session.flush()

        # Add item first time
        await cart_queries.add_item_to_cart(db_session, 1, 1, 1)

        # Add same item again
        cart = await cart_queries.add_item_to_cart(db_session, 1, 1, 2)

        assert cart is not None
        assert len(cart.info.items) == 1
        assert cart.info.items[0].quantity == 3  # 1 + 2
        assert cart.info.price == 6.0

    async def test_add_item_to_nonexistent_cart(self, db_session):
        """Test adding item to non-existent cart returns None"""
        db_session.add(ItemDB(id=1, name="Item", price=10.0, deleted=False))
        await db_session.flush()

        result = await cart_queries.add_item_to_cart(db_session, 999, 1, 1)
        assert result is None

    async def test_add_nonexistent_item_to_cart(self, db_session):
        """Test adding non-existent item to cart returns None"""
        db_session.add(CartDB(id=1, price=0.0))
        await db_session.flush()

        result = await cart_queries.add_item_to_cart(db_session, 1, 999, 1)
        assert result is None


class TestCartQueriesRemoveItemFromCart:
    """Tests for cart_queries.remove_item_from_cart function"""

    async def test_remove_item_from_cart(self, db_session):
        """Test removing item from cart"""
        # Create items and cart
        db_session.add_all([
            ItemDB(id=1, name="Item1", price=10.0, deleted=False),
            ItemDB(id=2, name="Item2", price=20.0, deleted=False),
        ])
        await db_session.flush()

        info = CartInfo(
            items=[
                CartItemInfo(id=1, name="Item1", quantity=1, available=True),
                CartItemInfo(id=2, name="Item2", quantity=1, available=True),
            ],
            price=0.0
        )
        cart = await cart_queries.add(db_session, info)
        assert cart.info.price == 30.0

        # Remove one item
        updated = await cart_queries.remove_item_from_cart(db_session, cart.id, 1)

        assert updated is not None
        assert len(updated.info.items) == 1
        assert updated.info.items[0].id == 2
        assert updated.info.price == 20.0

    async def test_remove_nonexistent_item_from_cart(self, db_session):
        """Test removing non-existent item from cart returns None"""
        db_session.add(CartDB(id=1, price=0.0))
        await db_session.flush()

        result = await cart_queries.remove_item_from_cart(db_session, 1, 999)
        assert result is None

    async def test_remove_item_from_nonexistent_cart(self, db_session):
        """Test removing item from non-existent cart returns None"""
        result = await cart_queries.remove_item_from_cart(db_session, 999, 1)
        assert result is None


class TestCalculatePrice:
    """Tests for cart_queries._calculate_price helper function"""

    async def test_calculate_price_empty_cart(self, db_session):
        """Test calculating price of empty cart"""
        db_session.add(CartDB(id=1, price=0.0))
        await db_session.flush()

        price = await cart_queries._calculate_price(db_session, 1)
        assert price == 0.0

    async def test_calculate_price_with_items(self, db_session):
        """Test calculating price with multiple items"""
        # Create items
        db_session.add_all([
            ItemDB(id=1, name="Item1", price=10.0, deleted=False),
            ItemDB(id=2, name="Item2", price=5.0, deleted=False),
        ])
        await db_session.flush()

        # Create cart
        info = CartInfo(
            items=[
                CartItemInfo(id=1, name="Item1", quantity=2, available=True),
                CartItemInfo(id=2, name="Item2", quantity=3, available=True),
            ],
            price=0.0
        )
        cart = await cart_queries.add(db_session, info)

        # Calculate price
        price = await cart_queries._calculate_price(db_session, cart.id)
        assert price == 35.0  # 10*2 + 5*3
