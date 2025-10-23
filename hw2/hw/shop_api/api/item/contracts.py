from pydantic import BaseModel
from typing import List, Optional

class ItemBase(BaseModel):
    name: str
    price: float

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int
    deleted: bool

    class Config:
        from_attributes = True

class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

    class Config:
        extra = "forbid"
