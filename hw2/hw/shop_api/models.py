from pydantic import BaseModel, NonNegativeFloat, NonNegativeInt, PositiveInt

class CreateItemRequest(BaseModel):
    name: str
    price: float

class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False
    
class CartResponseItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool
    
class CartResponse(BaseModel):
    id: int
    items: list[CartResponseItem]
    price: float

class Cart(BaseModel):
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


class GetCartsRequest(BaseModel):
    offset: NonNegativeInt = 0
    limit: PositiveInt = 10
    min_price: NonNegativeFloat = None
    max_price: NonNegativeFloat = None
    min_quantity: NonNegativeInt = None
    max_quantity: NonNegativeInt = None
    
    
class GetItemsRequest(BaseModel):
    offset: NonNegativeInt = 0
    limit: PositiveInt = 10
    min_price: NonNegativeFloat = None
    max_price: NonNegativeFloat = None
    show_deleted: bool = False
    
class UpdateItemRequest(BaseModel):
    name: str = None
    price: float = None
    
    class Config:
        extra = "forbid" 
        
class GeneratedID(BaseModel):
    id: int