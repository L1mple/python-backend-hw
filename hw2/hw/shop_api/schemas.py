from pydantic import BaseModel, ConfigDict, Field, conlist


class ElementId(BaseModel):
    id: int


class ItemRequest(BaseModel):
    name: str
    price: float


class PatchItemRequest(BaseModel):
    name: str | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")
    
    
class ItemResponse(ElementId):
    deleted: bool = Field(default=False)
    

class CartItem(ElementId):
    name: str
    quantity: int
    available: bool
    

class Cart(ElementId):
    price: float
    items: conlist(CartItem)