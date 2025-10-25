from pydantic import BaseModel
from typing import List, Optional

class ItemBase(BaseModel):
    name: str
    price: float

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int
    name: str
    price: float
    deleted: bool = False

class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    price: float
