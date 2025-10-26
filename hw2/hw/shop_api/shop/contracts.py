from __future__ import annotations
from typing import List

from pydantic import BaseModel, ConfigDict

from ..data.schemas import Item, PatchItem, CartItem, Cart

class ItemResponse(BaseModel):
    id : int | None
    name : str
    price : float
    deleted : bool

    @staticmethod
    def from_entity(entity : Item) -> ItemResponse:
        return ItemResponse(
            id=entity.id,
            name=entity.name,
            price=entity.price,
            deleted=entity.deleted
        )

class ItemRequest(BaseModel):
    name : str
    price : float

    def as_item(self) -> Item:
        return Item(name=self.name, price=self.price, deleted=False)

class PatchItemRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name : str | None = None
    price : float | None = None

    def as_patch_item(self) -> PatchItem:
        return PatchItem(name=self.name, price=self.price)

class CartItemResponse(BaseModel):
    id : int
    item_id : int
    name : str
    price : float
    quantity : int
    available : bool

    @staticmethod
    def from_entity(entity : CartItem) -> CartItemResponse:
        return CartItemResponse(
            id=entity.id, item_id=entity.item_id, name=entity.name, price=entity.price,
            quantity=entity.quantity, available=entity.available
        )

class CartResponse(BaseModel):
    id : int | None
    items : List[CartItemResponse]
    price : float
    quantity : int

    @staticmethod
    def from_entity(entity : Cart) -> CartResponse:
        return CartResponse(
            id=entity.id,
            items=[CartItemResponse.from_entity(item) for item in entity.items],
            price=entity.price,
            quantity=entity.quantity
        )
