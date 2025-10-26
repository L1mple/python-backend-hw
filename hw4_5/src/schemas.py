from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID


class CartCreate(BaseModel):
    pass

class CartCreateResponse(BaseModel):
    id: UUID

class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    quantity: float
    available: bool


class CartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    items: List[CartItemResponse] = []
    price: float


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    price: float


class ItemUpdate(ItemCreate):
    pass

class ItemPatch(ItemCreate):
    name: Optional[str] = None
    price: Optional[float] = None

class ItemResponse(ItemCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deleted: bool


class Msg(BaseModel):
    msg: str