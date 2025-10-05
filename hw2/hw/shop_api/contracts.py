from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from .store.storage import CartData, ItemnInCartData, ItemData, ItemsData

class IdModel(BaseModel):
    """
    Model handles with id 
    """
    id: int = Field(description="Returns id")

class ItemRequest(BaseModel):
    name: str = Field(description="item name")
    price: float = Field(gt=0, description="item price")

class ItemPatchRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0.0)
    
class ItemModel(BaseModel):
    """
    Model defines items
    """

    id: int = Field(description="item id, int")
    name: str = Field(description="item name, str")
    price: float = Field(description="item price, float")
    deleted: bool = Field(default=False, description="item available. bool")    
    @staticmethod
    def from_entity(entity: ItemData) -> "ItemModel":
        return ItemModel(
            id=entity.id,
            name=entity.name,
            price=entity.price,
            deleted=entity.deleted
        )

class ListQueryModel(BaseModel):
    offset: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(10, gt=0, description="Maximum number of items to return")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    show_deleted: bool = Field(False, description="Include deleted items")
    min_quantity: Optional[int] = Field(None, ge=0, description="Minimum quantity filter")
    max_quantity: Optional[int] = Field(None, ge=0, description="Maximum quantity filter")
    
class CartItemModel(BaseModel):
    """Model defines items in cart"""
    id: int = Field(description="item id")
    name: str = Field(description="item name") 
    quantity: int = Field(description="quantity in cart")
    available: bool = Field(description="is item available (not deleted)")

class CartResponseModel(BaseModel):
    """Models defines Carts"""
    id: int = Field(description="cart id")
    items: List[CartItemModel] = Field(description="items in cart")
    price: float = Field(description="total cart price")
    
    @staticmethod
    def from_entity(entity: CartData) -> "CartResponseModel":
        return CartResponseModel(
            id=entity.id,
            items=[CartItemModel(
                id=item.id,
                name=item.name, 
                quantity=item.quantity,
                available=item.available
            ) for item in entity.items],
            price=entity.price
        )