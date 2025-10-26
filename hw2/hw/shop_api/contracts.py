from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from hw2.hw.shop_api.models import CartEntity, CartItemEntity, ItemEntity, ItemInfo, PatchItemInfo

class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    price: float
    
    @staticmethod
    def from_entity(entity: CartEntity) -> CartResponse:
        return CartResponse(
            id = entity.id,
            items = [CartItemResponse.from_entity(entity) for entity in entity.info.items],
            price = entity.info.price
        )
        
class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool
    
    @staticmethod
    def from_entity(entity: CartItemEntity) -> CartItemResponse:
        return CartItemResponse(
            id = entity.id,
            name = entity.info.name,
            quantity = entity.info.quantity,
            available= entity.info.available
        )
        
class PatchItemRequest(BaseModel):
    name: str | None = None
    price: float | None = None
    
    model_config = ConfigDict(extra="forbid")
    
    def as_patch_item_info(self) -> PatchItemInfo:
        return PatchItemInfo(name = self.name, price = self.price)    
        
class PutItemRequest(BaseModel):
    name: str
    price: float
        
class ItemRequest(BaseModel):
    name: str
    price: float
    
    def as_item_info(self) -> ItemInfo:
        return ItemInfo(name = self.name, price = self.price, deleted=False)
        
class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool
    
    @staticmethod
    def from_entity(entity: ItemEntity) -> ItemResponse:
        return ItemResponse(
            id = entity.id,
            name = entity.info.name,
            price = entity.info.price,
            deleted = entity.info.deleted
        )