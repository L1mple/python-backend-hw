from __future__ import annotations
from typing import Any

from pydantic import BaseModel

from shop_api.cart.store.models import CartEntity, CartInfo, CartItemInfo


class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


# class CartItemRequest(BaseModel):
#     items: list[CartItemInfo]
#     price: float

#     def as_cart_info(self) -> CartInfo:
#         items = [CartItemInfo(**item.dict()) for item in self.items]
#         # price = 
#         return CartInfo(items=items, price=self.price)



class CartResponse(BaseModel):
    id: int
    items: list[CartItemInfo]
    price: float

    @staticmethod
    def from_entity(entity: CartEntity) -> CartResponse:
        return CartResponse(
            id=entity.id,
            items=entity.info.items,
            price=entity.info.price,
        )