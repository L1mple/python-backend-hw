from pydantic import BaseModel, ConfigDict

from .db_models import Item, Cart, CartItem


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool


class ItemRequest(BaseModel):
    name: str
    price: float
    deleted: bool = False


class ItemMapper:
    @staticmethod
    def to_domain(orm_item: Item) -> ItemResponse:
        return ItemResponse(
            id=orm_item.id,
            name=orm_item.name,
            price=orm_item.price,
            deleted=orm_item.deleted,
        )

    @staticmethod
    def to_orm(domain_item: ItemRequest, orm_item: Item | None = None) -> Item:
        if orm_item is None:
            orm_item = Item()
        orm_item.name = domain_item.name
        orm_item.price = domain_item.price
        orm_item.deleted = domain_item.deleted
        return orm_item


class PatchItemRequest(BaseModel):
    name: str | None = None
    price: float | None = None
    model_config = ConfigDict(extra="forbid")


class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    price: float


class CartItemMapper:
    @staticmethod
    def to_domain(orm_cart_item: CartItem) -> CartItemResponse:
        return CartItemResponse(
            id=orm_cart_item.item.id,
            name=orm_cart_item.item.name,
            quantity=orm_cart_item.quantity,
            available=not orm_cart_item.item.deleted,
        )


class CartMapper:
    @staticmethod
    def to_domain(orm_cart: Cart) -> CartResponse:
        return CartResponse(
            id=orm_cart.id,
            items=[CartItemMapper.to_domain(ci) for ci in orm_cart.items],
            price=orm_cart.price,
        )


class CartIdResponse(BaseModel):
    id: int
