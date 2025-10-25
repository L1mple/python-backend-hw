from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from shop_api.store.models import (
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
)


class ItemResponse(BaseModel):
    """Response model for item - what clients receive"""

    id: int
    name: str
    price: float
    deleted: bool

    @staticmethod
    def from_entity(entity: ItemEntity) -> ItemResponse:
        """Convert internal ItemEntity to API response"""
        return ItemResponse(
            id=entity.id,
            name=entity.info.name,
            price=entity.info.price,
            deleted=entity.info.deleted,
        )


class ItemRequest(BaseModel):
    """Request model for creating/replacing items (POST, PUT)"""

    name: str
    price: float

    def as_item_info(self) -> ItemInfo:
        """Convert API request to internal ItemInfo"""
        return ItemInfo(name=self.name, price=self.price)


class PatchItemRequest(BaseModel):
    """Request model for partial item updates (PATCH)"""

    name: str | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")

    def as_patch_item_info(self) -> PatchItemInfo:
        """Convert API patch request to internal PatchItemInfo"""
        return PatchItemInfo(name=self.name, price=self.price)
