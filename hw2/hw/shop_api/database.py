from typing import Dict

class Database:
    def __init__(self):
        self.items: Dict[int, dict] = {}
        self.carts: Dict[int, dict] = {}
        self._next_item_id = 1
        self._next_cart_id = 1
            
    def get_next_item_id(self) -> int:
        item_id = self._next_item_id
        self._next_item_id += 1
        return item_id
    
    def get_next_cart_id(self) -> int:
        cart_id = self._next_cart_id
        self._next_cart_id += 1
        return cart_id

db = Database()