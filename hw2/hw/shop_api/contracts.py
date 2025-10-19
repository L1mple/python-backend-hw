from typing import (
    List,
    Optional,
)
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
)
from hw import store


class ItemCreate(BaseModel):
    name: str
    price: float = Field(ge=0)


class ItemPut(BaseModel):
    name: str
    price: float = Field(ge=0)


class ItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)


class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool

    @staticmethod
    def item_to_out(item: store.Item) -> "ItemOut":
        return ItemOut(id=item.id, name=item.name, price=item.price, deleted=item.deleted)


class CartItemOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    price: float

    @staticmethod
    def cart_to_out(cart: store.Cart) -> "CartOut":
        items_out = []
        for ci in cart.items:
            items_out.append({
                "id": ci.id,
                "name": ci.name,
                "quantity": ci.quantity,
                "available": ci.available,
            })
        return CartOut(id=cart.id, items=items_out, price=cart.price)
