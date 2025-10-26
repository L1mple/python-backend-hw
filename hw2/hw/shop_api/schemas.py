from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ItemCreate(BaseModel):
    name: str
    price: float


class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    model_config = ConfigDict(extra="forbid")


class ItemOut(BaseModel):
    id: int
    name: str
    price: float
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

    class Config:
        orm_mode = True
