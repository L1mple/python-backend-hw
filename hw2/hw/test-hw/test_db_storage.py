"""Tests for shop_api.store.db_storage module"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from shop_api.store.db_storage import DBStorage
from shop_api.database import ItemDB, CartDB, CartItemDB
from shop_api.store.storage import ItemData, CartData, ItemnInCartData


class TestDBStorageAddItem:
    """Test DBStorage.add_item method"""

    @patch("shop_api.store.db_storage.uuid.uuid4")
    def test_add_item_success(self, mock_uuid):
        """Test adding item successfully"""
        mock_uuid.return_value.hex = "12345678abcd"
        mock_db = Mock()
        storage = DBStorage(db=mock_db)

        result = storage.add_item(name="Test Item", price=25.5)

        assert isinstance(result, ItemData)
        assert result.name == "Test Item"
        assert result.price == 25.5
        assert result.deleted is False
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


class TestDBStorageCreateCart:
    """Test DBStorage.create_cart method"""

    @patch("shop_api.store.db_storage.uuid.uuid4")
    def test_create_cart_success(self, mock_uuid):
        """Test creating cart successfully"""
        mock_uuid.return_value.hex = "abcdef123456"
        mock_db = Mock()
        storage = DBStorage(db=mock_db)

        result = storage.create_cart()

        assert isinstance(result, CartData)
        assert result.items == []
        assert result.price == 0.0
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


class TestDBStorageGetItem:
    """Test DBStorage.get_item method"""

    def test_get_item_success(self):
        """Test getting item successfully"""
        mock_db = Mock()
        mock_item = Mock(spec=ItemDB)
        mock_item.id = 1
        mock_item.name = "Item"
        mock_item.price = 10.0
        mock_item.deleted = False

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_item
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)
        result = storage.get_item(id=1)

        assert result.id == 1
        assert result.name == "Item"
        assert result.price == 10.0
        assert result.deleted is False

    def test_get_item_not_found(self):
        """Test getting non-existent item raises KeyError"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)

        with pytest.raises(KeyError, match="Item 999 not found"):
            storage.get_item(id=999)

    def test_get_item_deleted(self):
        """Test getting deleted item raises KeyError"""
        mock_db = Mock()
        mock_item = Mock(spec=ItemDB)
        mock_item.id = 1
        mock_item.deleted = True

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_item
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)

        with pytest.raises(KeyError, match="Item 1 not found"):
            storage.get_item(id=1)


class TestDBStorageGetCart:
    """Test DBStorage.get_cart method"""

    def test_get_cart_empty(self):
        """Test getting empty cart"""
        mock_db = Mock()
        mock_cart = Mock(spec=CartDB)
        mock_cart.id = 1
        mock_cart.price = 0.0
        mock_cart.cart_items = []

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_cart
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)
        result = storage.get_cart(id=1)

        assert result.id == 1
        assert result.items == []
        assert result.price == 0.0

    def test_get_cart_with_items(self):
        """Test getting cart with items"""
        mock_db = Mock()

        mock_item1 = Mock()
        mock_item1.id = 10
        mock_item1.name = "Item1"
        mock_item1.deleted = False

        mock_item2 = Mock()
        mock_item2.id = 20
        mock_item2.name = "Item2"
        mock_item2.deleted = True

        mock_cart_item1 = Mock()
        mock_cart_item1.item = mock_item1
        mock_cart_item1.quantity = 3

        mock_cart_item2 = Mock()
        mock_cart_item2.item = mock_item2
        mock_cart_item2.quantity = 1

        mock_cart = Mock(spec=CartDB)
        mock_cart.id = 5
        mock_cart.price = 50.0
        mock_cart.cart_items = [mock_cart_item1, mock_cart_item2]

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_cart
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)
        result = storage.get_cart(id=5)

        assert result.id == 5
        assert len(result.items) == 2
        assert result.items[0].id == 10
        assert result.items[0].quantity == 3
        assert result.items[0].available is True
        assert result.items[1].id == 20
        assert result.items[1].available is False

    def test_get_cart_not_found(self):
        """Test getting non-existent cart raises KeyError"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)

        with pytest.raises(KeyError, match="Cart 999 not found"):
            storage.get_cart(id=999)


class TestDBStorageGetItems:
    """Test DBStorage.get_items method"""

    def test_get_items_defaults(self):
        """Test getting items with default parameters"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)
        result = storage.get_items()

        assert result == []
        mock_query.filter.assert_called()
        mock_query.offset.assert_called_with(0)
        mock_query.limit.assert_called_with(10)

    def test_get_items_with_filters(self):
        """Test getting items with price filters"""
        mock_db = Mock()

        mock_item = Mock()
        mock_item.id = 1
        mock_item.name = "Item"
        mock_item.price = 15.0
        mock_item.deleted = False

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_item]
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)
        result = storage.get_items(min_price=10.0, max_price=20.0)

        assert len(result) == 1
        assert result[0].price == 15.0

    def test_get_items_show_deleted(self):
        """Test getting items with show_deleted=True"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)
        storage.get_items(show_deleted=True)

        # Should not filter by deleted when show_deleted=True
        # We just verify the query was built (specific assertion depends on implementation)
        mock_query.offset.assert_called()


class TestDBStorageGetCarts:
    """Test DBStorage.get_carts method"""

    def test_get_carts_empty(self):
        """Test getting carts returns empty list"""
        mock_db = Mock()
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)
        result = storage.get_carts()

        assert result == []

    def test_get_carts_with_quantity_filter(self):
        """Test getting carts with quantity filter"""
        mock_db = Mock()

        mock_item = Mock()
        mock_item.id = 1
        mock_item.name = "Item"
        mock_item.deleted = False

        mock_cart_item = Mock()
        mock_cart_item.item = mock_item
        mock_cart_item.quantity = 5

        mock_cart = Mock(spec=CartDB)
        mock_cart.id = 1
        mock_cart.price = 50.0
        mock_cart.cart_items = [mock_cart_item]

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_cart]
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)
        result = storage.get_carts(min_quantity=3, max_quantity=10)

        assert len(result) == 1
        assert result[0].id == 1

    def test_get_carts_filtered_by_min_quantity(self):
        """Test carts filtered out by min_quantity"""
        mock_db = Mock()

        mock_cart = Mock(spec=CartDB)
        mock_cart.id = 1
        mock_cart.price = 10.0
        mock_cart.cart_items = []  # No items, quantity = 0

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_cart]
        mock_db.query.return_value = mock_query

        storage = DBStorage(db=mock_db)
        result = storage.get_carts(min_quantity=1)

        # Cart with 0 items should be filtered out
        assert len(result) == 0


class TestDBStorageAddItemToCart:
    """Test DBStorage.add_item_to_cart method"""

    @patch.object(DBStorage, '_recalculate_cart_price')
    def test_add_item_to_cart_success_new_item(self, mock_recalc):
        """Test adding new item to cart"""
        mock_db = Mock()

        mock_cart = Mock(spec=CartDB)
        mock_cart.id = 1
        mock_cart.cart_items = []

        mock_item = Mock(spec=ItemDB)
        mock_item.id = 10
        mock_item.price = 15.0

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_cart,  # First call returns cart
            mock_item,  # Second call returns item
            None,       # Third call returns None (item not in cart yet)
        ]

        storage = DBStorage(db=mock_db)

        result = storage.add_item_to_cart(cart_id=1, item_id=10)

        assert result is True
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch.object(DBStorage, '_recalculate_cart_price')
    def test_add_item_to_cart_increment_quantity(self, mock_recalc):
        """Test adding existing item increments quantity"""
        mock_db = Mock()

        mock_cart = Mock(spec=CartDB)
        mock_item = Mock(spec=ItemDB)

        mock_cart_item = Mock()
        mock_cart_item.quantity = 2

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_cart,
            mock_item,
            mock_cart_item,  # Item already in cart
        ]

        storage = DBStorage(db=mock_db)

        result = storage.add_item_to_cart(cart_id=1, item_id=10)

        assert result is True
        assert mock_cart_item.quantity == 3
        mock_db.commit.assert_called_once()

    def test_add_item_to_cart_cart_not_found(self):
        """Test adding item to non-existent cart"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        storage = DBStorage(db=mock_db)
        result = storage.add_item_to_cart(cart_id=999, item_id=10)

        assert result is False

    def test_add_item_to_cart_item_not_found(self):
        """Test adding non-existent item to cart"""
        mock_db = Mock()
        mock_cart = Mock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_cart,
            None,  # Item not found
        ]

        storage = DBStorage(db=mock_db)
        result = storage.add_item_to_cart(cart_id=1, item_id=999)

        assert result is False


class TestDBStoragePutItem:
    """Test DBStorage.put_item method"""

    @patch.object(DBStorage, '_update_affected_carts')
    def test_put_item_success(self, mock_update_carts):
        """Test updating item with put"""
        mock_db = Mock()

        mock_item = Mock(spec=ItemDB)
        mock_item.id = 1
        mock_item.name = "Old Name"
        mock_item.price = 10.0
        mock_item.deleted = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        storage = DBStorage(db=mock_db)

        result = storage.put_item(item_id=1, name="New Name", price=25.0)

        assert result.name == "New Name"
        assert result.price == 25.0
        assert mock_item.name == "New Name"
        assert mock_item.price == 25.0
        mock_update_carts.assert_called_once_with(1)
        mock_db.commit.assert_called_once()

    def test_put_item_not_found(self):
        """Test putting non-existent item raises KeyError"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        storage = DBStorage(db=mock_db)

        with pytest.raises(KeyError, match="Item 999 not found"):
            storage.put_item(item_id=999, name="Test", price=10.0)


class TestDBStoragePatchItem:
    """Test DBStorage.patch_item method"""

    def test_patch_item_name_only(self):
        """Test patching item name only"""
        mock_db = Mock()

        mock_item = Mock(spec=ItemDB)
        mock_item.id = 1
        mock_item.name = "Old"
        mock_item.price = 10.0
        mock_item.deleted = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        storage = DBStorage(db=mock_db)
        result = storage.patch_item(item_id=1, name="New", price=None)

        assert result.name == "New"
        assert mock_item.name == "New"
        mock_db.commit.assert_called_once()

    @patch.object(DBStorage, '_update_affected_carts')
    def test_patch_item_price_only(self, mock_update_carts):
        """Test patching item price only"""
        mock_db = Mock()

        mock_item = Mock(spec=ItemDB)
        mock_item.id = 1
        mock_item.name = "Item"
        mock_item.price = 10.0
        mock_item.deleted = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        storage = DBStorage(db=mock_db)

        result = storage.patch_item(item_id=1, name=None, price=20.0)

        assert result.price == 20.0
        assert mock_item.price == 20.0
        mock_update_carts.assert_called_once_with(1)

    @patch.object(DBStorage, '_update_affected_carts')
    def test_patch_item_both_fields(self, mock_update_carts):
        """Test patching both name and price"""
        mock_db = Mock()

        mock_item = Mock(spec=ItemDB)
        mock_item.id = 1
        mock_item.name = "Old"
        mock_item.price = 10.0
        mock_item.deleted = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        storage = DBStorage(db=mock_db)

        result = storage.patch_item(item_id=1, name="New", price=25.0)

        assert result.name == "New"
        assert result.price == 25.0

    def test_patch_item_not_found(self):
        """Test patching non-existent item raises KeyError"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        storage = DBStorage(db=mock_db)

        with pytest.raises(KeyError):
            storage.patch_item(item_id=999, name="Test", price=10.0)


class TestDBStorageSoftDeleteItem:
    """Test DBStorage.soft_delete_item method"""

    @patch.object(DBStorage, '_update_affected_carts')
    def test_soft_delete_item_success(self, mock_update_carts):
        """Test soft deleting item"""
        mock_db = Mock()

        mock_item = Mock(spec=ItemDB)
        mock_item.id = 1
        mock_item.name = "Item"
        mock_item.price = 10.0
        mock_item.deleted = False

        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        storage = DBStorage(db=mock_db)

        result = storage.soft_delete_item(item_id=1)

        assert result.deleted is True
        assert mock_item.deleted is True
        mock_update_carts.assert_called_once_with(1)
        mock_db.commit.assert_called_once()

    def test_soft_delete_item_not_found(self):
        """Test soft deleting non-existent item raises KeyError"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        storage = DBStorage(db=mock_db)

        with pytest.raises(KeyError):
            storage.soft_delete_item(item_id=999)


class TestDBStorageRecalculateCartPrice:
    """Test DBStorage._recalculate_cart_price method"""

    def test_recalculate_cart_price_empty(self):
        """Test recalculating price for empty cart"""
        mock_db = Mock()
        storage = DBStorage(db=mock_db)

        mock_cart = Mock(spec=CartDB)
        mock_cart.cart_items = []
        mock_cart.price = 100.0

        storage._recalculate_cart_price(mock_cart)

        assert mock_cart.price == 0.0

    def test_recalculate_cart_price_with_items(self):
        """Test recalculating price with items"""
        mock_db = Mock()
        storage = DBStorage(db=mock_db)

        mock_item1 = Mock()
        mock_item1.price = 10.0

        mock_item2 = Mock()
        mock_item2.price = 20.0

        mock_cart_item1 = Mock()
        mock_cart_item1.item = mock_item1
        mock_cart_item1.quantity = 2

        mock_cart_item2 = Mock()
        mock_cart_item2.item = mock_item2
        mock_cart_item2.quantity = 3

        mock_cart = Mock(spec=CartDB)
        mock_cart.cart_items = [mock_cart_item1, mock_cart_item2]
        mock_cart.price = 0.0

        storage._recalculate_cart_price(mock_cart)

        # 10*2 + 20*3 = 20 + 60 = 80
        assert mock_cart.price == 80.0


class TestDBStorageUpdateAffectedCarts:
    """Test DBStorage._update_affected_carts method"""

    def test_update_affected_carts_no_carts(self):
        """Test updating when item is not in any cart"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        storage = DBStorage(db=mock_db)
        storage._update_affected_carts(item_id=1)

        # Should complete without errors

    @patch.object(DBStorage, '_recalculate_cart_price')
    def test_update_affected_carts_with_carts(self, mock_recalc):
        """Test updating carts containing the item"""
        mock_db = Mock()

        mock_cart_item1 = Mock()
        mock_cart_item1.cart_id = 10

        mock_cart_item2 = Mock()
        mock_cart_item2.cart_id = 20

        mock_cart1 = Mock(spec=CartDB)
        mock_cart2 = Mock(spec=CartDB)

        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_cart_item1,
            mock_cart_item2,
        ]

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_cart1,
            mock_cart2,
        ]

        storage = DBStorage(db=mock_db)

        storage._update_affected_carts(item_id=5)

        assert mock_recalc.call_count == 2
