from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# from hw2.hw.shop_api.models import (
from .models import (
    CartEntity,
    CartItem,
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
)


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool

    @staticmethod
    def from_entity(entity: ItemEntity) -> ItemResponse:
        return ItemResponse(
            id=entity.id,
            name=entity.info.name,
            price=entity.info.price,
            deleted=entity.info.deleted,
        )


class ItemRequest(BaseModel):
    name: str
    price: float

    def as_item_info(self) -> ItemInfo:
        return ItemInfo(
            name=self.name,
            price=self.price,
            deleted=False,
        )


class PatchItemRequest(BaseModel):
    name: str | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")

    def as_patch_item_info(self) -> PatchItemInfo:
        return PatchItemInfo(
            name=self.name,
            price=self.price,
            deleted=None,
        )


class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

    @staticmethod
    def from_cart_item(cart_item: CartItem) -> CartItemResponse:
        return CartItemResponse(
            id=cart_item.id,
            name=cart_item.name,
            quantity=cart_item.quantity,
            available=cart_item.available,
        )


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    price: float

    @staticmethod
    def from_entity(entity: CartEntity) -> CartResponse:
        return CartResponse(
            id=entity.id,
            items=[CartItemResponse.from_cart_item(item) for item in entity.items],
            price=entity.price,
        )

class PutItemRequest(BaseModel):
    name: str
    price: float
    
    model_config = ConfigDict(extra="forbid")
    
    def as_item_info(self) -> ItemInfo:
        return ItemInfo(
            name=self.name,
            price=self.price,
            deleted=False,
        )