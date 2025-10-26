from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0)

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0)
    deleted: Optional[bool] = False

class ItemPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, ge=0)
    model_config = ConfigDict(extra='forbid')

class ItemOut(ItemBase):
    id: int
    deleted: bool

    class Config:
        from_attributes = True

class ItemInCartOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartOut(BaseModel):
    id: int
    items: List[ItemInCartOut]
    price: float
