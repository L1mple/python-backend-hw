from __future__ import annotations
from pydantic import BaseModel, ConfigDict, field_validator
from shop_api.item.store.models import ItemEntity, ItemInfo, PatchItemInfo

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
            deleted=entity.info.deleted
        )

class ItemRequest(BaseModel):
    name: str
    price: float
    deleted: bool = False

    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('Le prix ne peut pas être négatif')
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Le nom ne peut pas être vide')
        return v.strip()

    def as_item_info(self) -> ItemInfo:
        return ItemInfo(name=self.name, price=self.price, deleted=self.deleted)

class PatchItemRequest(BaseModel):
    name: str | None = None
    price: float | None = None
    model_config = ConfigDict(extra="forbid")

    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Le prix ne peut pas être négatif')
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Le nom ne peut pas être vide')
        return v.strip() if v else v

    def as_patch_item_info(self) -> PatchItemInfo:
        return PatchItemInfo(name=self.name, price=self.price)