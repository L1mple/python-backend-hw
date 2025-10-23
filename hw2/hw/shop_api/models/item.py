from pydantic import BaseModel
from typing import Optional


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool


class ItemCreate(BaseModel):
    name: str
    price: float


class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

    class Config:
        extra = "forbid"


class ItemPut(BaseModel):
    name: str
    price: float
    deleted: Optional[bool] = None
