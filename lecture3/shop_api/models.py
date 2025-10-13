from fastapi import Query
from typing import List, Optional
from pydantic import BaseModel, Field


class NotFoundError(Exception):
    pass

class NotModifiedError(Exception):
    pass

class Item(BaseModel):
    id: int = Field(..., gt=0)
    name: str = Field(...)
    price: float = Field(..., gt=0)
    deleted: bool = Field(False)

class CartItem(BaseModel):
    id: int = Field(..., gt=0)
    name: str = Field(...)
    quantity: int = Field(1, gt=0)
    available: bool = Field(...)

class Cart(BaseModel):
    id: int = Field(..., gt=0)
    items: List[CartItem] = Field(default_factory=list)
    price: float = Field(0, ge=0)

class CartFilterParams:
    def __init__(
        self,
        offset: int = Query(0, ge=0, description="Смещение по списку"),
        limit: int = Query(10, gt=0, description="Ограничение на количество"),
        min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена включительно"),
        max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена включительно"),
        min_quantity: Optional[int] = Query(None, ge=0, description="Минимальное число товаров"),
        max_quantity: Optional[int] = Query(None, ge=0, description="Максимальное число товаров")
    ):
        self.offset = offset
        self.limit = limit
        self.min_price = min_price
        self.max_price = max_price
        self.min_quantity = min_quantity
        self.max_quantity = max_quantity

class ItemFilterParams:
    def __init__(
        self,
        offset: int = Query(0, ge=0, description="Смещение по списку"),
        limit: int = Query(10, gt=0, description="Ограничение на количество"),
        min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена включительно"),
        max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена включительно"),
        show_deleted: Optional[bool] = Query(False, description="Показывать ли удаленные товары")
    ):
        self.offset = offset
        self.limit = limit
        self.min_price = min_price
        self.max_price = max_price
        self.show_deleted = show_deleted

class ItemRequest(BaseModel):
    name: str = Field(..., description="Название товара")
    price: float = Field(..., ge=0, description="Цена товара")

class ItemPatchRequest(BaseModel):
    name: Optional[str] = Field(None, description="Новое название товара")
    price: Optional[float] = Field(None, description="Новая цена товара")

    model_config = {"extra": "forbid"}

class CartCreateResponse(BaseModel):
    id: int = Field(..., gt=0, description="ID корзины")
