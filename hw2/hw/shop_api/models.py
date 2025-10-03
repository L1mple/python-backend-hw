from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional


# ----- Item -----
class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0.0)


class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0.0)


class ItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, ge=0.0)


class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool


# ----- Cart -----
class CartItemOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    price: float
