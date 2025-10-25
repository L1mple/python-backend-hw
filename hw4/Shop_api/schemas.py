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
        from_attributes = True

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool
    

class Cart(BaseModel):
    id: int
    items: List[CartItem]
    total_price: float

    class Config:
        from_attributes = True
        
class ItemSchema(BaseModel):
    id: int
    name: str
    price: float
    available: bool

    class Config:
        orm_mode = True

class CartItemSchema(BaseModel):
    item: ItemSchema
    quantity: int

    class Config:
        orm_mode = True

class CartSchema(BaseModel):
    id: int
    total_price: float
    items: List[CartItemSchema] = []

    class Config:
        orm_mode = True

