from pydantic import BaseModel


class ItemInfo(BaseModel):
    name: str
    price: float
    deleted: bool = False


class ItemEntity(BaseModel):
    id: int
    info: ItemInfo


class PatchItemInfo(BaseModel):
    name: str | None = None
    price: float | None = None


class CartItemInfo(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartInfo(BaseModel):
    items: list[CartItemInfo] = []


class CartEntity(BaseModel):
    id: int
    info: CartInfo
