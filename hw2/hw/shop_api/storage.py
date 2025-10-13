from typing import Any, Dict, Optional


class Storage:
    def __init__(self):
        self.items_db: Dict[int, Dict[str, Any]] = {}
        self.carts_db: Dict[int, Dict[str, Any]] = {}
        self.next_item_id = 1
        self.next_cart_id = 1

    def get_item_by_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        return self.items_db.get(item_id)

    def get_cart_by_id(self, cart_id: int) -> Optional[Dict[str, Any]]:
        return self.carts_db.get(cart_id)

    def create_item(self, item_data: Dict[str, Any]) -> int:
        item_id = self.next_item_id
        self.next_item_id += 1
        
        new_item = {
            "id": item_id,
            "name": item_data["name"],
            "price": item_data["price"],
            "deleted": False
        }
        self.items_db[item_id] = new_item
        return item_id

    def create_cart(self) -> int:
        cart_id = self.next_cart_id
        self.next_cart_id += 1
        
        new_cart = {
            "id": cart_id,
            "items": {}
        }
        self.carts_db[cart_id] = new_cart
        return cart_id

    def update_item(self, item_id: int, update_data: Dict[str, Any]) -> None:
        if item_id in self.items_db:
            self.items_db[item_id].update(update_data)

    def delete_item(self, item_id: int) -> None:
        if item_id in self.items_db:
            self.items_db[item_id]["deleted"] = True

    def add_item_to_cart(self, cart_id: int, item_id: int) -> None:
        if cart_id in self.carts_db:
            if "items" not in self.carts_db[cart_id]:
                self.carts_db[cart_id]["items"] = {}
            
            current_quantity = self.carts_db[cart_id]["items"].get(str(item_id), 0)
            self.carts_db[cart_id]["items"][str(item_id)] = current_quantity + 1

    def get_all_items(self) -> list[Dict[str, Any]]:
        return list(self.items_db.values())

    def get_all_carts(self) -> list[Dict[str, Any]]:
        return list(self.carts_db.values())

    def calculate_cart_price(self, cart: Dict[str, Any]) -> float:
        total_price = 0.0
        for item_id, quantity in cart.get("items", {}).items():
            item = self.get_item_by_id(int(item_id))
            if item and not item.get("deleted", False):
                total_price += item["price"] * quantity
        return total_price


storage = Storage()
