from pydantic import BaseModel, ConfigDict, PositiveInt, PositiveFloat, NonNegativeInt, NonNegativeFloat
from typing import Optional


class BaseItem(BaseModel):
    name: str
    price: PositiveFloat

    model_config = ConfigDict(extra="forbid")


class PatchItem(BaseModel):
    name: Optional[str] = None
    price: Optional[PositiveFloat] = None

    model_config = ConfigDict(extra="forbid")


class Item(BaseItem):
    id: int
    deleted: bool


class CartItem(BaseModel):
    id: int
    name: str
    quantity: PositiveInt
    available: bool


class Cart(BaseModel):
    id: int
    items: list[CartItem]
    price: float


class CartFilters(BaseModel):
    offset: NonNegativeInt = 0
    limit: PositiveInt = 10
    min_price: NonNegativeFloat | None = None
    max_price: NonNegativeFloat | None = None
    min_quantity: NonNegativeInt | None = None
    max_quantity: NonNegativeInt | None = None


class ItemFilters(BaseModel):
    offset: NonNegativeInt = 0
    limit: PositiveInt = 10
    min_price: NonNegativeFloat | None = None
    max_price: NonNegativeFloat | None = None
    show_deleted: bool = False
