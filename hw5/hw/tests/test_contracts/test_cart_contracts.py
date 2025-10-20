import pytest
from shop_api.cart.contracts import CartItemResponse, CartResponse
from shop_api.cart.store.models import CartEntity, CartInfo, CartItemInfo

class TestCartContracts:
    def test_cart_item_response(self):
        """Test CartItemResponse"""
        response = CartItemResponse(
            id=1, 
            name="Test Item", 
            quantity=2, 
            available=True
        )
        
        assert response.id == 1
        assert response.name == "Test Item"
        assert response.quantity == 2
        assert response.available is True
    
    def test_cart_response_from_entity(self):
        """Test la conversion d'Entity vers Response"""
        items = [
            CartItemInfo(id=1, name="Item1", quantity=1, available=True),
            CartItemInfo(id=2, name="Item2", quantity=3, available=False)
        ]
        entity = CartEntity(id=1, info=CartInfo(items=items, price=400.0))
        
        response = CartResponse.from_entity(entity)
        
        assert response.id == 1
        assert response.price == 400.0
        assert len(response.items) == 2
        assert response.items[0].name == "Item1"
        assert response.items[1].quantity == 3
        assert response.items[1].available is False