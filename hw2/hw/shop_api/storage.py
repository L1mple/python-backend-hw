from typing import Dict, List, Optional
from .models import Item, Cart, CartItem, ItemCreate, ItemUpdate


class Storage:
    def __init__(self):
        self.items: Dict[int, Item] = {}
        self.carts: Dict[int, Cart] = {}
        self._next_item_id = 1
        self._next_cart_id = 1

    def create_item(self, item_data: ItemCreate) -> Item:
        item_id = self._next_item_id
        self._next_item_id += 1
        item = Item(id=item_id, **item_data.model_dump())
        self.items[item_id] = item
        return item

    def get_item(self, item_id: int) -> Optional[Item]:
        return self.items.get(item_id)

    def get_available_item(self, item_id: int) -> Optional[Item]:
        item = self.items.get(item_id)
        return item if item and not item.deleted else None

    def list_items(self, show_deleted: bool = False) -> List[Item]:
        items = list(self.items.values())
        if not show_deleted:
            items = [item for item in items if not item.deleted]
        return items

    def replace_item(self, item_id: int, item_data: ItemCreate) -> Optional[Item]:
        if item_id not in self.items:
            return None

        current_deleted = self.items[item_id].deleted
        self.items[item_id] = Item(
            id=item_id,
            **item_data.model_dump(),
            deleted=current_deleted
        )
        return self.items[item_id]

    def update_item(self, item_id: int, update_data: ItemUpdate) -> Optional[Item]:
        if item_id not in self.items:
            return None

        item = self.items[item_id]
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(item, field, value)

        return item

    def delete_item(self, item_id: int) -> Optional[Item]:
        if item_id not in self.items:
            return None
        self.items[item_id].deleted = True
        return self.items[item_id]

    def create_cart(self) -> int:
        cart_id = self._next_cart_id
        self._next_cart_id += 1
        cart = Cart(id=cart_id, items=[], price=0.0)
        self.carts[cart_id] = cart
        return cart_id

    def get_cart(self, cart_id: int) -> Optional[Cart]:
        return self.carts.get(cart_id)

    def add_item_to_cart(self, cart_id: int, item_id: int) -> bool:
        if cart_id not in self.carts:
            return False

        item = self.get_available_item(item_id)
        if not item:
            return False

        cart = self.carts[cart_id]

        cart_item = CartItem(
            id=item_id,
            name=item.name,
            quantity=1,
            available=True
        )
        cart.items.append(cart_item)

        cart.price = sum(
            cart_item.quantity * self.items[cart_item.id].price
            for cart_item in cart.items
            if cart_item.available
        )

        return True

storage = Storage()