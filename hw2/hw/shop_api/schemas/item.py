from pydantic import BaseModel, Field
from typing import Optional


class ItemBase(BaseModel):
    name: str
    price: float = Field(..., ge=0)

class ItemCreate(ItemBase):
    pass

class Item(ItemBase):
    id: int
    deleted: bool = False

class ItemPatch(BaseModel):
    name: Optional[str]
    price: Optional[float]