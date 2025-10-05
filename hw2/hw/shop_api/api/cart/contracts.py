from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Iterable

from shop_api.store.models import (
    CartItemInfo,
    CartEntity,
    CartInfo
)


# class CartItemResponse(BaseModel):
#     id: int
#     name: str
#     quantity: int
#     available: bool

#     @staticmethod
#     def from_entity(entity: CartItemEntity) -> CartItemResponse:
#         return CartItemResponse(
#             id=entity.id,
#             name=entity.info.name,
#             quantity=entity.info.quantity,
#             available=entity.info.available
#         )


class CartResponse(BaseModel):
    id: int
    items: Iterable[CartItemInfo]
    price: float

    @staticmethod
    def from_entity(entity: CartEntity) -> CartResponse:
        return CartResponse(
            id=entity.id,
            items=entity.info.items,
            price=entity.info.price,
        )