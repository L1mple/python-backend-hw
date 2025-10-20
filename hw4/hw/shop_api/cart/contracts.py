from __future__ import annotations
from pydantic import BaseModel
from shop_api.cart.store.models import CartEntity, CartInfo, CartItemInfo

class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    price: float

    @staticmethod
    def from_entity(entity: CartEntity) -> CartResponse:
        items = [CartItemResponse(id=item.id, name=item.name, quantity=item.quantity, available=item.available) for item in entity.info.items]
        return CartResponse(id=entity.id, items=items, price=entity.info.price)