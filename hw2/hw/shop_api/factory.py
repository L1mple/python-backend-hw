from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)

class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartResponse(BaseModel):
    id: int
    items: List[CartItem]
    price: float
    created_at: datetime

    class Config:
            from_attributes = True # для конвертация ORM в pydantic

