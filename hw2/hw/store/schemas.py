from pydantic import BaseModel
from typing import List, Optional

class ItemBase(BaseModel):
    name: str
    price: float

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    deleted: bool

    class Config:
        orm_mode = True


class CartItem(BaseModel):
    id: int
    item_id: int
    quantity: int

    class Config:
        orm_mode = True


class Cart(BaseModel):
    id: int
    total_price: float
    items: List[CartItem] = []

    class Config:
        orm_mode = True
