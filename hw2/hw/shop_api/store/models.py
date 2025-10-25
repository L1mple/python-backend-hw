from dataclasses import dataclass


@dataclass(slots=True)
class ItemInfo:
    name: str
    price: float
    deleted: bool = False


@dataclass(slots=True)
class ItemEntity:
    id: int
    info: ItemInfo


@dataclass(slots=True)
class PatchItemInfo:
    """
    Частичное обновление товара по id (разрешено менять все поля, кроме deleted)
    """

    name: str | None = None
    price: float | None = None


@dataclass(slots=True)
class CartItemEntity:
    item_id: int
    item_name: str
    quantity: int
    available: bool


@dataclass(slots=True)
class CartInfo:
    items: list[CartItemEntity]


@dataclass(slots=True)
class CartEntity:
    id: int
    info: CartInfo
