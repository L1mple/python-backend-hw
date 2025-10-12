from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ItemBase(BaseModel):
    """базовыая модель товара"""

    name: str
    """наименование товара"""
    price: float
    """цена товара"""


class Item(ItemBase):
    """товар"""

    id: int
    """идентификатор товара"""
    deleted: bool = False
    """удален ли товар"""


class ItemUpdate(BaseModel):
    """частичное обновление товара"""

    model_config = ConfigDict(extra='forbid')

    name: Optional[str] = None
    """наименование товара"""
    price: Optional[float] = None
    """цена товара"""


class CartItem(BaseModel):
    """товар в корзине"""

    id: int
    """идентификатор товара"""
    name: str
    """наименование товара"""
    quantity: int
    """количество товара в корзине"""
    available: bool
    """доступен ли (не удален) товар"""


class Cart(BaseModel):
    """корзина"""

    id: int
    """идентификатор корзины"""
    items: List[CartItem]
    """список товаров в корзине"""
    price: float
    """общая сумма товаров в корзине"""
