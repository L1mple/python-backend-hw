from pydantic import BaseModel, ConfigDict, Field


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

    model_config = ConfigDict(from_attributes=True)


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

    model_config = ConfigDict(from_attributes=True)


class Cart(BaseModel):
    id: int
    items: list[CartItem] = Field(default_factory=list)
    price: float = 0.0

    model_config = ConfigDict(from_attributes=True)
