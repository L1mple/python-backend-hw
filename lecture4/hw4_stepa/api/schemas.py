from pydantic import BaseModel
from typing import List, Optional

class ProductData(BaseModel):
    title: str
    cost: float

class ProductCreate(ProductData):
    pass

class ProductInfo(ProductData):
    id: int
    is_removed: bool = False

class BasketProductInfo(BaseModel):
    id: int
    title: str
    amount: int
    is_active: bool

class BasketInfo(BaseModel):
    id: int
    items: List[BasketProductInfo]
    total_cost: float
