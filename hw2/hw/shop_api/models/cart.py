from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CartItemResponse(BaseModel):
    id: int
    quantity: int = Field(ge=1, description="Количество товара должно быть больше 0")


class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    price: float = Field(ge=0, description="Цена не может быть отрицательной")


class CartCreateResponse(BaseModel):
    id: int


class CartListQuery(BaseModel):
    offset: Optional[int] = Field(None, ge=0, description="Смещение для пагинации")
    limit: Optional[int] = Field(None, gt=0, le=100, description="Лимит записей (максимум 100)")
    min_price: Optional[float] = Field(None, ge=0, description="Минимальная цена")
    max_price: Optional[float] = Field(None, ge=0, description="Максимальная цена")
    min_quantity: Optional[int] = Field(None, ge=0, description="Минимальное количество товаров")
    max_quantity: Optional[int] = Field(None, ge=0, description="Максимальное количество товаров")