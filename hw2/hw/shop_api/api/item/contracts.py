from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from decimal import Decimal

from .store.models import ItemEntity, ItemInfo, PatchItemInfo

class ItemResponse(BaseModel):
    id: int
    name: str
    price: Decimal
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
    price: Decimal

    def as_item_info(self) -> ItemInfo:
        return ItemInfo(name=self.name, price=self.price)


class PatchItemRequest(BaseModel):
    name: str | None = None
    price: Decimal | None = None

    model_config = ConfigDict(extra="forbid")

    def as_patch_item_info(self) -> PatchItemInfo:
        return PatchItemInfo(name=self.name, price=self.price)
