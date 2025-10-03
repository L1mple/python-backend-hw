from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# Pydantic-модели для валидации запросов/ответов
class ItemCreate(BaseModel):
    """Модель для создания товара"""

    name: str  # Название товара
    price: float = Field(..., gt=0)  # Цена > 0


class ItemUpdate(BaseModel):
    """Модель для полной замены товара"""

    name: str
    price: float = Field(..., gt=0)


class ItemPatch(BaseModel):
    """Модель для частичного обновления товара"""

    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    model_config = ConfigDict(extra="forbid")  # Запрещаем лишние поля


class ItemResponse(BaseModel):
    """Ответ для товара"""

    id: int
    name: str
    price: float
    deleted: bool


class CartItem(BaseModel):
    """Товар в корзине"""

    id: int
    name: str
    quantity: int
    available: bool  # Доступен ли (не удалён)


class CartResponse(BaseModel):
    """Ответ для корзины"""

    id: int
    items: List[CartItem]
    price: float  # Общая цена
