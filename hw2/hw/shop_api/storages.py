from .schemas import Cart, Item, ItemCreate
from typing import Dict, List, Optional

carts_storage: Dict[int, Cart] = {}
items_storage: Dict[int, Item] = {}

cart_counter = 1
item_counter = 1


class CartStorage:
    @staticmethod
    def create() -> int:
        global cart_counter
        cart_id = cart_counter
        cart_counter += 1
        carts_storage[cart_id] = Cart(id=cart_id, items=[], price=0.0)
        return cart_id

    @staticmethod
    def get(cart_id: int) -> Optional[Cart]:
        return carts_storage.get(cart_id)

    @staticmethod
    def get_all() -> List[Cart]:
        return list(carts_storage.values())

    @staticmethod
    def update(cart: Cart):
        carts_storage[cart.id] = cart


class ItemStorage:
    @staticmethod
    def create(item: ItemCreate) -> Item:
        global item_counter
        item_id = item_counter
        item_counter += 1
        new_item = Item(id=item_id, **item.dict())
        items_storage[item_id] = new_item
        return new_item

    @staticmethod
    def get(item_id: int) -> Optional[Item]:
        return items_storage.get(item_id)

    @staticmethod
    def get_all() -> List[Item]:
        return list(items_storage.values())

    @staticmethod
    def update(item: Item):
        items_storage[item.id] = item

    @staticmethod
    def delete(item_id: int) -> bool:
        if item_id in items_storage:
            items_storage[item_id].deleted = True
            return True
        return False

    @staticmethod
    def exists(item_id: int) -> bool:
        return item_id in items_storage