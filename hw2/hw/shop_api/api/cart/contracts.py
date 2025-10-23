from pydantic import BaseModel
from typing import List, Optional

class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    price: float

class CartCreateResponse(BaseModel):
    id: int
