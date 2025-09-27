import pydantic


# Requests


class GetCartsRequest(pydantic.BaseModel):
    offset: pydantic.NonNegativeInt = 0
    limit: pydantic.PositiveInt = 10
    min_price: pydantic.NonNegativeFloat | None = None
    max_price: pydantic.NonNegativeFloat | None = None
    min_quantity: pydantic.NonNegativeInt | None = None
    max_quantity: pydantic.NonNegativeInt | None = None


class CreateItemRequest(pydantic.BaseModel):
    name: str
    price: float


class UpdateItemRequest(pydantic.BaseModel):
    name: str | None = None
    price: float | None = None

    model_config = pydantic.ConfigDict(extra="forbid")


class GetItemsRequest(pydantic.BaseModel):
    offset: pydantic.NonNegativeInt = 0
    limit: pydantic.PositiveInt = 10
    min_price: pydantic.NonNegativeFloat | None = None
    max_price: pydantic.NonNegativeFloat | None = None
    show_deleted: bool = False


# Responses


class WrappedID(pydantic.BaseModel):
    id: int


class CartResponseItem(pydantic.BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartResponse(pydantic.BaseModel):
    id: int
    items: list[CartResponseItem]
    price: float


# Objects


class Item(pydantic.BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False


class Cart(pydantic.BaseModel):
    id: int
    items: dict[int, int]

    def create_cart_response(self, items: dict[int, Item]) -> tuple[CartResponse, int]:
        price = 0.0
        total_quantity = 0
        prepated_items = []

        for item_id, quantity in self.items.items():
            item = items[item_id]
            total_quantity += quantity
            price += item.price * quantity
            prepated_items.append(
                CartResponseItem(
                    id=item.id,
                    name=item.name,
                    quantity=quantity,
                    available=(not item.deleted),
                )
            )

        return CartResponse(
            id=self.id, items=prepated_items, price=price
        ), total_quantity
