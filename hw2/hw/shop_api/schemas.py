from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class ItemIn(BaseModel):
    name: str
    price: float

class ItemOut(ItemIn):
    id: int
    deleted: bool = False

class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    model_config = ConfigDict(extra="forbid")

class CartItemOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    price: float
