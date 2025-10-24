from typing import List

from pydantic import BaseModel

from hw2.hw.shop_api.store.models import (
    CartEntity,
    AddItemInfo
)


class ItemCartResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartResponse(BaseModel):
    id: int
    items: List[ItemCartResponse]
    price: float

    @staticmethod
    def from_entity(entity: CartEntity):
        return CartResponse(
            id=entity.id,
            items=[ItemCartResponse(id=item_id,
                                    name=info.name,
                                    quantity=info.quantity,
                                    available=info.available)
                   for item_id, info in entity.info.items.items()],
            price=entity.info.price
        )
