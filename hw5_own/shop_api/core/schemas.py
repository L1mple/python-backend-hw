# from __future__ import annotations
from typing import Optional, Annotated
from pydantic import BaseModel, Field, ConfigDict

ItemName = Annotated[str, Field(description="Наименование товара", min_length=1)]
ItemId = Annotated[int, Field(description="Идентификатор корзины", ge=0)]
ItemPrice = Annotated[float, Field(description="Цена товара", ge=0)]

CartId = Annotated[int, Field(description="Идентификатор корзины")]


# ---- Item ----
class ItemOut(BaseModel):
    id: ItemId
    name: ItemName
    price: ItemPrice
    deleted: bool = Field(description="Удален ли товар", default=False)


class ItemCreate(BaseModel):
    name: ItemName
    price: ItemPrice


class ItemPut(BaseModel):
    name: ItemName
    price: ItemPrice


class ItemPatch(BaseModel):
    # Разрешаем частичное обновление ТОЛЬКО name/price; лишние поля → 422
    model_config = ConfigDict(extra="forbid")

    name: Optional[ItemName] = None
    price: Optional[ItemPrice] = None


# ---- Cart ----
class CartItemView(BaseModel):
    id: ItemId
    name: ItemName
    quantity: int = Field(description="Количество товара в корзине", ge=0)
    available: bool = Field(description="Доступен ли товар")


class CartView(BaseModel):
    id: int
    items: list[CartItemView]
    price: float = Field(description="Общая сумма заказа", ge=0.0)
