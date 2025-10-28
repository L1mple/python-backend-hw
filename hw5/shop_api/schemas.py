from pydantic import BaseModel, Field
from typing import Optional, List


# --- Модели товаров ---

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, gt=0)
    available: Optional[bool] = True


# --- Модели корзины ---

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartCreate(BaseModel):
    items: List[CartItem] = []
    price: float = 0.0