from typing import List

from pydantic import BaseModel

from shop_api.store.models import Cart


class ItemCartResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartResponse(BaseModel):
    id: int
    items: List[ItemCartResponse]
    price: float

    @classmethod
    def from_orm(cls, cart: Cart):
        items = [
            ItemCartResponse(
                id=ci.item.id,
                name=ci.item.name,
                quantity=ci.quantity,
                available=not ci.item.deleted
            ) for ci in cart.items
        ]
        return cls(id=cart.id, items=items, price=cart.total_price)
