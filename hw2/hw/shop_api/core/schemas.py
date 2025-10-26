from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict

class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)

class ItemUpdatePut(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)

class ItemUpdatePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, ge=0)

class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool

class CartOutItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartOut(BaseModel):
    id: int
    items: list[CartOutItem]
    price: float
