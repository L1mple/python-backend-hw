from typing import Optional
class Storage:

    def __init__(self):
        self.items: dict[int, dict] = {}
        self.carts: dict[int, dict] = {}
        self.item_id_counter = 0
        self.cart_id_counter = 0

    def create_item(self, name: str, price: float) -> dict:
        self.item_id_counter += 1
        new_item = {
            "id": self.item_id_counter,
            "name": name,
            "price": price,
            "deleted": False
        }
        self.items[self.item_id_counter] = new_item
        return new_item

    def get_item(self, item_id: int) -> Optional[dict]:
        return self.items.get(item_id)

    def update_item(self, item_id: int, name: Optional[str] = None, price: Optional[float] = None) -> Optional[dict]:
        if item_id not in self.items:
            return None

        if name is not None:
            self.items[item_id]['name'] = name
        if price is not None:
            self.items[item_id]['price'] = price

        return self.items[item_id]

    def replace_item(self, item_id: int, name: str, price: float) -> Optional[dict]:
        if item_id not in self.items:
            return None

        self.items[item_id]['name'] = name
        self.items[item_id]['price'] = price
        return self.items[item_id]

    def delete_item(self, item_id: int) -> Optional[dict]:
        if item_id not in self.items:
            return None

        self.items[item_id]['deleted'] = True
        return self.items[item_id]

    def get_all_items(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        show_deleted: bool = False
    ) -> list[dict]:
        all_items = list(self.items.values())

        if not show_deleted:
            all_items = [item for item in all_items if not item['deleted']]

        if min_price is not None:
            all_items = [item for item in all_items if item['price'] >= min_price]
        if max_price is not None:
            all_items = [item for item in all_items if item['price'] <= max_price]

        return all_items[offset:offset + limit]


    def create_cart(self) -> int:
        self.cart_id_counter += 1
        self.carts[self.cart_id_counter] = {
            "id": self.cart_id_counter,
            "items": {}  # {item_id: quantity}
        }
        return self.cart_id_counter

    def get_cart(self, cart_id: int) -> Optional[dict]:
        if cart_id not in self.carts:
            return None

        cart_data = self.carts[cart_id]
        items_list = []
        total_price = 0.0

        for item_id, quantity in cart_data["items"].items():
            item = self.get_item(item_id)
            if item:
                available = not item['deleted']
                items_list.append({
                    "id": item_id,
                    "name": item['name'],
                    "quantity": quantity,
                    "available": available
                })

                if available:
                    total_price += item['price'] * quantity

        return {
            "id": cart_id,
            "items": items_list,
            "price": total_price
        }

    def add_item_to_cart(self, cart_id: int, item_id: int) -> bool:
        if cart_id not in self.carts:
            return False
        if item_id not in self.items:
            return False

        cart = self.carts[cart_id]
        if item_id in cart["items"]:
            cart["items"][item_id] += 1
        else:
            cart["items"][item_id] = 1

        return True

    def get_all_carts(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None
    ) -> list[dict]:
        all_carts = []

        for cart_id in self.carts:
            cart = self.get_cart(cart_id)
            if cart:
                if min_price is not None and cart['price'] < min_price:
                    continue
                if max_price is not None and cart['price'] > max_price:
                    continue

                total_quantity = sum(item['quantity'] for item in cart['items'])
                if min_quantity is not None and total_quantity < min_quantity:
                    continue
                if max_quantity is not None and total_quantity > max_quantity:
                    continue

                all_carts.append(cart)

        return all_carts[offset:offset + limit]


storage = Storage()