from pydantic import BaseModel
from typing import List

from shop_api.cart.store.schemas import CartEntity

class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    price: float

    @staticmethod
    def from_entity(entity: "CartEntity") -> "CartResponse":
        return CartResponse(
            id=entity.id,
            items=[
                CartItemResponse(
                    id=item.id,
                    name=item.name,
                    quantity=item.quantity,
                    available=item.available,
                )
                for item in entity.items
            ],
            price=entity.price,
        )