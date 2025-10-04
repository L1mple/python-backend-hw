from pydantic import BaseModel, ConfigDict


class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    price: float

    model_config = ConfigDict(from_attributes=True)


class CartCreateResponse(BaseModel):
    id: int

    model_config = ConfigDict(from_attributes=True)
