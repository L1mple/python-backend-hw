from typing import List
from pydantic import BaseModel, Field, computed_field

from shop_api.models.item import ItemSchema


class CartOutSchema(BaseModel):
    id: str
    items: List[ItemSchema] = Field(default_factory=list)

    @computed_field
    @property
    def price(self) -> float:
        return sum(item.price * item.quantity for item in self.items)
