from __future__ import annotations

from pydantic import BaseModel

from shop_api.store.models import (
    CartEntity,
    CartItemEntity,
)


class CartItemResponse(BaseModel):
    """Response model for a cart item"""

    id: int
    name: str
    quantity: int
    available: bool

    @staticmethod
    def from_entity(entity: CartItemEntity) -> CartItemResponse:
        """Convert internal CartItemEntity to API response"""
        return CartItemResponse(
            id=entity.item_id,
            name=entity.item_name,
            quantity=entity.quantity,
            available=entity.available,
        )


class CartResponse(BaseModel):
    """Response model for cart with calculated price"""

    id: int
    items: list[CartItemResponse]
    price: float

    @staticmethod
    def from_entity(entity: CartEntity) -> CartResponse:
        """Convert internal CartEntity to API response with calculated price"""
        from shop_api.store import queries

        # Convert cart items
        items = [CartItemResponse.from_entity(item) for item in entity.info.items]

        # Calculate total price
        total_price = 0.0
        for cart_item in entity.info.items:
            # Get the item to access its price
            item_entity = queries.get_item(cart_item.item_id)
            if item_entity:
                total_price += item_entity.info.price * cart_item.quantity

        return CartResponse(
            id=entity.id,
            items=items,
            price=total_price,
        )


class CartIdResponse(BaseModel):
    """Response model for cart creation (returns just the ID)"""

    id: int

    @staticmethod
    def from_entity(entity: CartEntity) -> CartIdResponse:
        """Convert internal CartEntity to simple ID response"""
        return CartIdResponse(id=entity.id)
