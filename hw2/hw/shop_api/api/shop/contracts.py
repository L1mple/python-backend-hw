from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ...data.models import (
    CartItemInfo,
    CartInfo,
    CartEntity,
    PatchCartInfo,
    ItemInfo,
    ItemEntity,
    PatchItemInfo,
)


class CartResponse(BaseModel):
    id: int
    items: list[CartItemInfo]
    price: float

    @staticmethod
    def from_entity(entity: CartEntity) -> CartResponse:
        return CartResponse(
            id=entity.id, items=entity.info.items, price=entity.info.price
        )


class CartRequest(BaseModel):
    items: list[CartItemInfo] = []
    price: float = 0.0

    def as_cart_info(self) -> CartInfo:
        return CartInfo(items=self.items, price=self.price)


class PatchCartRequest(BaseModel):
    items: list[CartItemInfo] | None = None

    model_config = ConfigDict(extra="forbid")

    def as_patch_cart_info(self) -> PatchCartInfo:
        return PatchCartInfo(items=self.items)


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
        return ItemInfo(name=self.name, price=self.price, deleted=False)


class PatchItemRequest(BaseModel):
    name: str | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")

    def as_patch_item_info(self) -> PatchItemInfo:
        return PatchItemInfo(name=self.name, price=self.price, deleted=None)
