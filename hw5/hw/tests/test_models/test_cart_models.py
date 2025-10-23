import pytest
from shop_api.cart.store.models import CartItemInfo, CartInfo, CartEntity

class TestCartModels:
    def test_cart_item_info_creation(self):
        """Test la création d'un CartItemInfo"""
        item_info = CartItemInfo(id=1, name="Test Item", quantity=3, available=True)
        
        assert item_info.id == 1
        assert item_info.name == "Test Item"
        assert item_info.quantity == 3
        assert item_info.available is True
    
    def test_cart_info_creation(self):
        """Test la création d'un CartInfo"""
        items = [
            CartItemInfo(id=1, name="Item1", quantity=2, available=True),
            CartItemInfo(id=2, name="Item2", quantity=1, available=False)
        ]
        cart_info = CartInfo(items=items, price=300.0)
        
        assert len(cart_info.items) == 2
        assert cart_info.price == 300.0
        assert cart_info.items[0].name == "Item1"
        assert cart_info.items[1].available is False
    
    def test_cart_entity_creation(self):
        """Test la création d'un CartEntity"""
        items = [CartItemInfo(id=1, name="Test", quantity=1, available=True)]
        cart_info = CartInfo(items=items, price=100.0)
        cart_entity = CartEntity(id=5, info=cart_info)
        
        assert cart_entity.id == 5
        assert cart_entity.info.price == 100.0
        assert len(cart_entity.info.items) == 1