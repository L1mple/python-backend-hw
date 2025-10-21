from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, description="Наименование товара", examples=["Молоко \"Бурёнка\" 1л"])
    price: float = Field(..., gt=0, description="Цена товара", examples=[159.99])

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = Field(None, min_length=1, description="Новое наименование товара", examples=["Молоко \"Новое\" 1л"])
    price: Optional[float] = Field(None, gt=0, description="Новая цена товара", examples=[169.99])

class Item(ItemBase):
    id: int = Field(..., description="Уникальный идентификатор товара", examples=[321])
    deleted: bool = Field(False, description="Товар удален (soft delete)")

class CartItem(BaseModel):
    id: int = Field(..., gt=0, description="ID товара", examples=[1])
    name: str = Field(..., min_length=1, description="Название товара", examples=["Туалетная бумага \"Поцелуй\", рулон"])
    quantity: int = Field(..., ge=1, description="Количество товара в корзине", examples=[3])
    available: bool = Field(..., description="Товар доступен для заказа")

class Cart(BaseModel):
    id: int = Field(..., description="Уникальный идентификатор корзины", examples=[123])
    items: List[CartItem] = Field(..., description="Список товаров в корзине")
    price: float = Field(..., description="Общая сумма заказа", examples=[234.4])

class CartCreateResponse(BaseModel):
    id: int = Field(..., description="Идентификатор созданной корзины", examples=[123])