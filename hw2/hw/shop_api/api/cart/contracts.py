from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from decimal import Decimal

from .store.models import (
    CartEntity,
    CartInfo,
    CardItem,
)


class CartResponse(BaseModel):
    id: int
    items: list[CardItem]
    price: Decimal

    @staticmethod
    def from_entity(entity: CartEntity) -> CartResponse:
        return CartResponse(
            id=entity.id,
            items=entity.info.items,
            price=entity.info.price,
        )


class CartRequest(BaseModel):
    info: CartInfo

    def as_cart_info(self) -> CartInfo:
        return self.info

