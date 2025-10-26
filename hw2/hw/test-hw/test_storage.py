"""Tests for shop_api.store.storage module (dataclasses)"""
import pytest
from shop_api.store.storage import ItemData, ItemsData, ItemnInCartData, CartData, IdDataGen


class TestItemData:
    """Test ItemData dataclass"""

    def test_item_data_creation(self):
        """Test ItemData creation with all fields"""
        item = ItemData(id=1, name="Test Item", price=10.99, deleted=False)
        assert item.id == 1
        assert item.name == "Test Item"
        assert item.price == 10.99
        assert item.deleted is False

    def test_item_data_default_deleted(self):
        """Test ItemData default deleted value"""
        item = ItemData(id=2, name="Item", price=5.0)
        assert item.deleted is False

    def test_item_data_deleted_true(self):
        """Test ItemData with deleted=True"""
        item = ItemData(id=3, name="Deleted", price=15.0, deleted=True)
        assert item.deleted is True


class TestItemsData:
    """Test ItemsData dataclass"""

    def test_items_data_empty(self):
        """Test ItemsData with empty items list"""
        items_data = ItemsData()
        assert items_data.items == []

    def test_items_data_with_items(self):
        """Test ItemsData with items"""
        item1 = ItemData(id=1, name="Item1", price=10.0)
        item2 = ItemData(id=2, name="Item2", price=20.0)
        items_data = ItemsData(items=[item1, item2])
        assert len(items_data.items) == 2
        assert items_data.items[0] == item1
        assert items_data.items[1] == item2


class TestItemInCartData:
    """Test ItemnInCartData dataclass"""

    def test_item_in_cart_creation(self):
        """Test ItemnInCartData creation"""
        cart_item = ItemnInCartData(id=1, name="Cart Item", quantity=5, available=True)
        assert cart_item.id == 1
        assert cart_item.name == "Cart Item"
        assert cart_item.quantity == 5
        assert cart_item.available is True

    def test_item_in_cart_unavailable(self):
        """Test ItemnInCartData with unavailable item"""
        cart_item = ItemnInCartData(id=2, name="Unavailable", quantity=1, available=False)
        assert cart_item.available is False


class TestCartData:
    """Test CartData dataclass"""

    def test_cart_data_empty(self):
        """Test CartData with default values"""
        cart = CartData(id=1)
        assert cart.id == 1
        assert cart.items == []
        assert cart.price == 0.0

    def test_cart_data_with_items(self):
        """Test CartData with items and price"""
        item1 = ItemnInCartData(id=1, name="Item1", quantity=2, available=True)
        item2 = ItemnInCartData(id=2, name="Item2", quantity=1, available=True)
        cart = CartData(id=5, items=[item1, item2], price=50.0)
        assert cart.id == 5
        assert len(cart.items) == 2
        assert cart.price == 50.0

    def test_cart_data_custom_price(self):
        """Test CartData with custom price"""
        cart = CartData(id=10, items=[], price=100.0)
        assert cart.price == 100.0


class TestIdDataGen:
    """Test IdDataGen dataclass"""

    def test_id_data_gen_creation(self):
        """Test IdDataGen creation"""
        id_gen = IdDataGen(id=12345)
        assert id_gen.id == 12345

    def test_id_data_gen_gen_id(self):
        """Test IdDataGen.gen_id generates unique IDs"""
        id1 = IdDataGen.gen_id()
        id2 = IdDataGen.gen_id()

        assert isinstance(id1, IdDataGen)
        assert isinstance(id2, IdDataGen)
        assert isinstance(id1.id, int)
        assert isinstance(id2.id, int)
        # UUIDs should be unique
        assert id1.id != id2.id

    def test_id_data_gen_gen_id_multiple(self):
        """Test IdDataGen.gen_id generates multiple unique IDs"""
        ids = [IdDataGen.gen_id().id for _ in range(10)]
        # All IDs should be unique
        assert len(ids) == len(set(ids))
