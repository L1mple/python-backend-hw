from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import List

from hw2.hw.shop_api.store.cart_models import (
    PatchCartInfo,
    CartEntity,
    CartInfo,
    CartItemInfo,
)


class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

    @staticmethod
    def from_cart_item_info(cart_item: CartItemInfo) -> CartItemResponse:
        return CartItemResponse(
            id=cart_item.id,
            name=cart_item.name,
            quantity=cart_item.quantity,
            available=cart_item.available,
        )


class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    price: float

    @staticmethod
    def from_entity(entity: CartEntity) -> CartResponse:
        return CartResponse(
            id=entity.id,
            items=[CartItemResponse.from_cart_item_info(item) for item in entity.info.items],
            price=entity.info.price,
        )


class CartItemRequest(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

    def as_cart_item_info(self) -> CartItemInfo:
        return CartItemInfo(
            id=self.id,
            name=self.name,
            quantity=self.quantity,
            available=self.available,
        )


class CartRequest(BaseModel):
    items: List[CartItemRequest]
    price: float

    def as_cart_info(self) -> CartInfo:
        return CartInfo(
            items=[item.as_cart_item_info() for item in self.items],
            price=self.price,
        )


class PatchCartItemRequest(BaseModel):
    id: int | None = None
    name: str | None = None
    quantity: int | None = None
    available: bool | None = None

    model_config = ConfigDict(extra="forbid")


class PatchCartRequest(BaseModel):
    items: List[CartItemRequest] | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")

    def as_patch_cart_info(self) -> PatchCartInfo:
        return PatchCartInfo(
            items=[item.as_cart_item_info() for item in self.items] if self.items else None,
            price=self.price,
        )
