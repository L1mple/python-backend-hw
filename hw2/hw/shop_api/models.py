from pydantic import BaseModel, ConfigDict
from typing import Optional


class ItemCreate(BaseModel):
    name: str
    price: float


class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: Optional[str] = None
    price: Optional[float] = None


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class Cart(BaseModel):
    id: int
    items: list[CartItem]
    price: float
