from __future__ import annotations

from pydantic import BaseModel
from typing import Iterable

from shop_api.store.models import (
    Cart,
    CartItem
)

class CartMapper:
    """Маппер для преобразования между CartResponse и Cart (ORM)"""

    @staticmethod
    def to_domain(orm_cart: Cart) -> CartResponse:
        """Преобразование ORM модели в доменную"""
        return CartResponse(
            id=orm_cart.id,
            items=[CartItemMapper.to_domain(item) for item in orm_cart.items],
            price=orm_cart.price
        )


class CartItemMapper:
    """Маппер для преобразования между CartItemResponse и CartItem (ORM)"""

    @staticmethod
    def to_domain(orm_cart_item: CartItem) -> CartItemResponse:
        """Преобразование ORM модели в доменную"""
        return CartItemResponse(
            id=orm_cart_item.id,
            name=orm_cart_item.item.name,
            quantity=orm_cart_item.quantity,
            available=not orm_cart_item.item.deleted
        )


class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartResponse(BaseModel):
    id: int
    items: Iterable[CartItemResponse]
    price: float
