from pydantic import BaseModel, ConfigDict
from typing import List, Optional



class CartCreateResponse(BaseModel):
    id: int

class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: float
    available: bool


class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse] = []
    price: float


class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    price: Optional[float] = None


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool


class Msg(BaseModel):
    msg: str