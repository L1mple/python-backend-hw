from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from .models import ItemResponse, CartResponse, CartItemResponse, ItemCreate

class ItemService:
    def __init__(self):
        self.items_db: List[ItemResponse] = []
        self.item_id_counter = 1

    def create_item(self, item: ItemCreate) -> ItemResponse:
        new_item = ItemResponse(
            id=self.item_id_counter,
            name=item.name,
            price=item.price,
            deleted=False
        )
        self.item_id_counter += 1
        self.items_db.append(new_item)
        return new_item

    def get_item(self, item_id: int) -> ItemResponse:
        item = next((i for i in self.items_db if i.id == item_id), None)
        if not item or item.deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return item

    def get_items(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        show_deleted: bool = False,
    ) -> List[ItemResponse]:
        filtered_items = [
            item for item in self.items_db
            if (show_deleted or not item.deleted) and
               (min_price is None or item.price >= min_price) and
               (max_price is None or item.price <= max_price)
        ]
        return filtered_items[offset:offset+limit]

    def replace_item(self, item_id: int, item: ItemCreate) -> ItemResponse:
        existing_item = next((i for i in self.items_db if i.id == item_id), None)
        if not existing_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        updated_item = ItemResponse(
            id=item_id,
            name=item.name,
            price=item.price,
            deleted=existing_item.deleted
        )
        self.items_db[self.items_db.index(existing_item)] = updated_item
        return updated_item

    def update_item(self, item_id: int, updates: Dict[str, Any]) -> ItemResponse:
        item = next((i for i in self.items_db if i.id == item_id), None)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        if item.deleted:
            raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED)

        if "deleted" in updates:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

        updated_item = item.copy(update=updates)
        self.items_db[self.items_db.index(item)] = updated_item
        return updated_item

    def delete_item(self, item_id: int) -> None:
        item = next((i for i in self.items_db if i.id == item_id), None)
        if not item:
            return
        item.deleted = True

class CartService:
    def __init__(self):
        self.carts_db: List[CartResponse] = []
        self.cart_id_counter = 1

    def create_cart(self) -> Dict[str, int]:
        cart_id = self.cart_id_counter
        self.cart_id_counter += 1
        self.carts_db.append(CartResponse(id=cart_id, items=[], price=0.0))
        return {"id": cart_id}

    def get_cart(self, cart_id: int) -> CartResponse:
        cart = next((c for c in self.carts_db if c.id == cart_id), None)
        if not cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
        return cart

    def get_carts(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
    ) -> List[CartResponse]:
        filtered_carts = []
        for cart in self.carts_db:
            total_quantity = sum(item.quantity for item in cart.items)
            if (
                (min_price is None or cart.price >= min_price) and
                (max_price is None or cart.price <= max_price) and
                (min_quantity is None or total_quantity >= min_quantity) and
                (max_quantity is None or total_quantity <= max_quantity)
            ):
                filtered_carts.append(cart)
        return filtered_carts[offset:offset+limit]

    def add_item_to_cart(self, cart_id: int, item_id: int, item_service: ItemService) -> None:
        cart = next((c for c in self.carts_db if c.id == cart_id), None)
        if not cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        item = item_service.get_item(item_id)
        existing_item = next((i for i in cart.items if i.id == item_id), None)
        if existing_item:
            existing_item.quantity += 1
        else:
            cart.items.append(CartItemResponse(
                id=item.id,
                name=item.name,
                quantity=1,
                available=not item.deleted
            ))

        cart.price = sum(
            item.quantity * item_service.get_item(item.id).price
            for item in cart.items
        )
