from pydantic import BaseModel, ConfigDict

from .models import CartEntity, CartItem, ItemEntity



class ItemRequest(BaseModel):
    name: str
    price: float


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

    @staticmethod
    def from_entity(entity: ItemEntity) -> "ItemResponse":
        return ItemResponse(
            id=entity.id,
            name=entity.name,
            price=entity.price,
            deleted=entity.deleted,
        )


class PatchItemRequest(BaseModel):
    name: str | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")



class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

    @staticmethod
    def from_cart_item(item: CartItem) -> "CartItemResponse":
        return CartItemResponse(
            id=item.id,
            name=item.name,
            quantity=item.quantity,
            available=item.available,
        )


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    price: float

    @staticmethod
    def from_entity(entity: CartEntity) -> "CartResponse":
        return CartResponse(
            id=entity.id,
            items=[CartItemResponse.from_cart_item(item) for item in entity.items],
            price=entity.price,
        )


class CartIdResponse(BaseModel):
    id: int
