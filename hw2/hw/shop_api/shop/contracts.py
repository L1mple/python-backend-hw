from __future__ import annotations
from typing import List

from pydantic import BaseModel, ConfigDict

from ..store.models import (
    ItemInfo,
    ItemEntity,
    PatchItemInfo,
    CartItemInfo,
    CartEntity
)

class ItemResponse(BaseModel):
    id : int
    name : str
    price : float
    deleted : bool

    @staticmethod
    def from_entity(entity : ItemEntity) -> ItemResponse:
        return ItemResponse(
            id=entity.id,
            name=entity.info.name,
            price=entity.info.price,
            deleted=entity.info.deleted
        )

class ItemRequest(BaseModel):
    name : str
    price : float

    def as_item_info(self) -> ItemInfo:
        return ItemInfo(self.name, self.price, False)

class PatchItemRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name : str | None = None
    price : float | None = None

    def as_patch_item_info(self) -> PatchItemInfo:
        return PatchItemInfo(self.name, self.price)

class CartItemResponse(BaseModel):
    id : int
    name : str
    price : float
    quantity : int
    available : bool

    @staticmethod
    def from_entity(entity : CartItemInfo) -> CartItemResponse:
        return CartItemResponse(
            id=entity.id, name=entity.name, price=entity.price,
            quantity=entity.quantity, available=entity.available
        )

class CartResponse(BaseModel):
    id : int
    items : List[CartItemResponse]
    price : float

    @staticmethod
    def from_entity(entity : CartEntity) -> CartResponse:
        return CartResponse(
            id=entity.id,
            items=[CartItemResponse.from_entity(item) for item in entity.info.items],
            price=entity.info.price
        )
