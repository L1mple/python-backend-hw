from typing import Optional, List

from pydantic import BaseModel, Field

# Определяет модели Pydantic: ItemCreate, ItemPut, ItemPatch, Item, CartItem, Cart

class ItemBase(BaseModel):
    name: str
    price: float = Field(ge=0)


class ItemCreate(ItemBase):
    pass


class ItemPut(ItemBase):
    pass


class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)

    class Config:
        extra = "forbid"
        validate_assignment = True


class Item(ItemBase):
    id: int
    deleted: bool = False


class CartItem(BaseModel):
    id: int
    quantity: int = Field(ge=1)


class Cart(BaseModel):
    id: int
    items: List[CartItem]
    price: float


