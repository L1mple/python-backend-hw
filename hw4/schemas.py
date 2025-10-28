from pydantic import BaseModel, confloat, conint, PositiveInt
from typing import List, Optional

class ItemBase(BaseModel):
    name: str
    price: confloat(ge=0.0)

    class Config:
        extra = 'forbid'


class ItemCreate(ItemBase):
    pass


class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[confloat(ge=0.0)] = None

    class Config:
        extra = 'forbid'


class Item(ItemBase):
    id: int
    deleted: bool

    class Config:
        orm_mode = True


class CartItemOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    price: float
