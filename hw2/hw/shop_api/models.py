from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic import BaseModel, Field, ConfigDict


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0)


class ItemPut(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0)
    deleted: bool = False


class ItemPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, ge=0)
    model_config = ConfigDict(extra='forbid')


model_config = {
    "extra": "forbid",
}


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
    items: List[CartItem]
    price: float
