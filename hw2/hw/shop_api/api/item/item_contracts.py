from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from hw2.hw.shop_api.store.item_models import (
    PatchItemInfo,
    ItemEntity,
    ItemInfo,
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
    deleted: bool = False

    def as_item_info(self) -> ItemInfo:
        return ItemInfo(name=self.name, price=self.price, deleted=self.deleted)


class PatchItemRequest(BaseModel):
    name: str | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")

    def as_patch_item_info(self) -> PatchItemInfo:
        return PatchItemInfo(name=self.name, price=self.price)
