from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# --- SQLAlchemy модели ---
# Используются для определения таблиц в PostgreSQL и взаимодействия с БД через SQLAlchemy.
# Наследуются от Base для маппинга на таблицы и поддержки асинхронных операций.

class Base(AsyncAttrs, DeclarativeBase):
    """Базовый класс для SQLAlchemy моделей, обеспечивает маппинг на таблицы и асинхронность"""
    pass


class Item(Base):
    """Модель таблицы товаров (items). Хранит информацию о товарах."""
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # Уникальный ID, автоинкремент
    name: Mapped[str] = mapped_column(String, nullable=False)  # Название товара, обязательно
    price: Mapped[float] = mapped_column(Float, nullable=False)  # Цена, обязательно, > 0 (валидируется в Pydantic)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # Флаг soft-delete


class Cart(Base):
    """Модель таблицы корзин (carts). Хранит корзины и их связь с товарами."""
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # Уникальный ID корзины
    items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    # Связь с CartItem, удаляет связанные элементы при удалении корзины


class CartItem(Base):
    """Модель таблицы связи корзин и товаров (cart_items). Хранит количество товаров в корзине."""
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # Уникальный ID записи
    cart_id: Mapped[int] = mapped_column(Integer, ForeignKey("carts.id"), nullable=False)  # Внешний ключ на carts
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id"), nullable=False)  # Внешний ключ на items
    quantity: Mapped[int] = mapped_column(Integer, default=1)  # Количество товара, по умолчанию 1

    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")  # Связь с корзиной
    item: Mapped["Item"] = relationship("Item")  # Связь с товаром


# --- Pydantic модели ---
# Используются для валидации запросов и форматирования ответов в FastAPI.
# Наследуются от BaseModel для автоматической валидации и сериализации в JSON.

class ItemCreate(BaseModel):
    """Модель для создания товара (POST /item). Валидирует входные данные."""
    name: str  # Название товара, обязательно
    price: float = Field(..., gt=0)  # Цена, обязательно, > 0


class ItemUpdate(BaseModel):
    """Модель для полной замены товара (PUT /item/{id}). Все поля обязательны."""
    name: str
    price: float = Field(..., gt=0)


class ItemPatch(BaseModel):
    """Модель для частичного обновления товара (PATCH /item/{id}). Поля опциональны."""
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)  # Цена, если указана, > 0
    model_config = ConfigDict(extra="forbid")  # Запрещает лишние поля в запросе


class ItemResponse(BaseModel):
    """Модель ответа для товара. Используется в GET-запросах."""
    id: int
    name: str
    price: float
    deleted: bool  # Флаг удаления


class CartItemResponse(BaseModel):
    """Модель ответа для товара в корзине. Используется в составе CartResponse."""
    id: int
    name: str
    quantity: int
    available: bool  # Доступен ли товар (не удалён)


class CartResponse(BaseModel):
    """Модель ответа для корзины. Используется в GET /cart и GET /cart/{id}."""
    id: int
    items: List[CartItemResponse]  # Список товаров в корзине
    price: float  # Общая цена корзины
    