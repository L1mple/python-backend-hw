from __future__ import annotations

from pydantic import BaseModel, ConfigDict, NonNegativeFloat

from shop_api.store.models import (
    CartEntity,
    CartItemInfo,
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
)


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

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
    price: NonNegativeFloat

    def as_item_info(self) -> ItemInfo:
        return ItemInfo(name=self.name, price=self.price, deleted=False)


class PatchItemRequest(BaseModel):
    name: str | None = None
    price: NonNegativeFloat | None = None

    model_config = ConfigDict(extra="forbid")

    def as_patch_item_info(self) -> PatchItemInfo:
        return PatchItemInfo(name=self.name, price=self.price)


class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

    @staticmethod
    def from_cart_item_info(info: CartItemInfo) -> CartItemResponse:
        return CartItemResponse(
            id=info.id,
            name=info.name,
            quantity=info.quantity,
            available=info.available,
        )


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    price: float

    @staticmethod
    def from_entity(entity: CartEntity, items_dict: dict[int, ItemEntity]) -> CartResponse:
        cart_items = [
            CartItemResponse.from_cart_item_info(item) 
            for item in entity.info.items
        ]
        
        total_price = 0.0
        for item in entity.info.items:
            if item.id in items_dict and item.available:
                total_price += items_dict[item.id].info.price * item.quantity
        
        return CartResponse(
            id=entity.id,
            items=cart_items,
            price=total_price,
        )


class CartIdResponse(BaseModel):
    id: int
