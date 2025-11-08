from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Optional

from shop_api.store.models import (
    Item
)



class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool


class ItemMapper:
    """Маппер для преобразования между ItemResponse и Item (ORM)"""

    @staticmethod
    def to_domain(orm_item: Item) -> ItemResponse:
        """Преобразование ORM модели в доменную"""
        return ItemResponse(
            id=orm_item.id,
            name=orm_item.name,
            price=orm_item.price,
            deleted=orm_item.deleted
        )

    @staticmethod
    def to_orm(
        domain_item: ItemRequest,
        orm_item: Optional[Item] = None,
    ) -> Item:
        """Преобразование доменной модели в ORM"""
        if orm_item is None:
            orm_item = Item()

        orm_item.name = domain_item.name
        orm_item.price = domain_item.price
        orm_item.deleted = domain_item.deleted

        return orm_item


class ItemRequest(BaseModel):
    name: str
    price: float
    deleted: bool = False
    

class PatchItemRequest(BaseModel):
    name: str | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")

