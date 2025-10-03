import json
import os
from typing import Literal


class DataStorage:
    def __init__(self, storage_path) -> None:
        self.storage_path = os.path.join(os.getcwd(), storage_path)
        
        self.item_storage_path = os.path.join(self.storage_path, "item_storage.json")
        self.cart_storage_path = os.path.join(self.storage_path, "cart_storage.json")
        
        self.init_storages()
        
        self.item_storage = self.open_storage(self.item_storage_path)
        self.cart_storage = self.open_storage(self.cart_storage_path)
        
        print("DataStorage init!")
    
    def init_storages(self):
        os.makedirs(self.storage_path, exist_ok=True)
        
        for st in [self.item_storage_path, self.cart_storage_path]:
            if os.path.exists(st):
                continue
            
            with open(st, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        
    def open_storage(self, storage):
        with open(storage, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
    
    def save_storage(self, storage: Literal["item", "cart"]):
        if storage not in ["item", "cart"]:
            return
        
        match storage:
            case "item":
                with open(self.item_storage_path, "w") as f:
                    json.dump(self.item_storage, f, indent=4)
            case "cart":
                with open(self.cart_storage_path, "w") as f:
                    json.dump(self.cart_storage, f, indent=4)
            case _:
                print("Not exist storage!")
                return
    
    def create_cart(self):
        try:
            next_cart_id = max(map(int, self.cart_storage.keys())) + 1
        except ValueError:
            next_cart_id = 1
        
        self.cart_storage[str(next_cart_id)] = {"id": next_cart_id, "items": {}}
        self.save_storage("cart")
        
        return next_cart_id
    
    def is_cart_exists(self, cart_id):
        return str(cart_id) in self.cart_storage
    
    def get_cart(self, cart_id):
        if str(cart_id) not in self.cart_storage:
            return None
        
        cart = {"id": cart_id, "items": []}
        total = 0
        
        for item_id, item_count in self.cart_storage[str(cart_id)]["items"].items():
            item = self.get_item(str(item_id))
            print(f"{item=}")
            cart["items"].append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "quantity": item_count,
                    "available": not item["deleted"],
                }
            )
            total += item_count * item["price"]
            
        cart["price"] = total
        
        return cart
    
    def get_carts(self):
        return [self.get_cart(cart_id) for cart_id in self.cart_storage]
    
    def create_item(self, name: str, price: float):
        try:
            next_item_id = max(map(int, self.item_storage.keys())) + 1
        except ValueError:
            next_item_id = 1
        
        item = {"id": next_item_id, "name": name, "price": price, "deleted": False}
        self.item_storage[str(next_item_id)] = item
        self.save_storage("item")
        
        return item
    
    def is_item_exists(self, item_id):
        return str(item_id) in self.item_storage
    
    def get_item(self, item_id):
        if str(item_id) not in self.item_storage:
            return None
        
        return self.item_storage[str(item_id)]
    
    def get_items(self):
        return list(self.item_storage.values())
    
    def update_item(self, item):
        if str(item["id"]) not in self.item_storage:
            return
        
        self.item_storage[str(item["id"])] = item
        self.save_storage("item")
    
    def add_item2storage(self, cart_id, item):
        items_in_cart = self.cart_storage[str(cart_id)]["items"].get(str(item["id"]), 0) + 1
        self.cart_storage[str(cart_id)]["items"][str(item["id"])] = items_in_cart
        self.save_storage("cart")
        