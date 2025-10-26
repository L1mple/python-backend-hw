from typing import List, Optional

from shop_api.models import CartItem, Cart, Item
from shop_api.models import CartNotFoundException, Item, ItemNotFoundException


class Repository:
    carts: List[Cart] = []
    items: List[Item] = []

    def create_cart(self) -> Cart:
        cart_id = len(self.carts)
        cart = Cart(id=cart_id, items=[], price=0.0)
        self.carts.append(cart)
        return cart.model_copy(deep=True)
    
    def _get_cart(self, cart_id: int) -> Cart:
        if cart_id >= len(self.carts):
            raise CartNotFoundException()
        return self.carts[cart_id]

    def get_cart(self, cart_id: int) -> Cart:
        return self._get_cart(cart_id).model_copy(deep=True)
    
    def get_carts(self, offset: int, limit: int) -> List[Cart]:
        return [cart.model_copy(deep=True) for cart in self.carts[offset:offset+limit]]
    
    def add_item_to_cart(self, cart_id: int, item_id: int):
        cart: Cart = self._get_cart(cart_id)
        item: Item = self.get_item(item_id)
        
        for cart_item in cart.items:
            if cart_item.id == item.id:
                cart_item.quantity += 1
                break
        else:
            cart.items.append(CartItem(id=item.id, name=item.name, quantity=1,
                                       available=not item.deleted))

        cart.price += item.price

    def create_item(self, name: str, price: float) -> Item:
        item_id = len(self.items)
        item = Item(id=item_id, name=name, price=price, deleted=False)
        self.items.append(item)
        return item.model_copy(deep=True)
    
    def _get_item(self, item_id: int) -> Item:
        if item_id >= len(self.items):
            raise ItemNotFoundException()
        return self.items[item_id]
    
    def get_item(self, item_id: int) -> Item:
        item: Item = self._get_item(item_id)
        if item.deleted:
            raise ItemNotFoundException()

        return item.model_copy(deep=True)

    def get_items(self, offset: int, limit: int) -> List[Item]:
        return [item.model_copy(deep=True) for item in self.items[offset:offset+limit]]
    
    def replace_item(self, item_id: int, name: str, price: float) -> Item:
        if item_id >= len(self.items):
            raise ItemNotFoundException()

        item = Item(id=item_id, name=name, price=price, deleted=False)
        self.items[item_id] = item
        return item.model_copy(deep=True)
    
    def update_item(self, item_id: int, name: Optional[str], price: Optional[float]) -> Optional[Item]:
        item: Item = self._get_item(item_id)
        
        if item.deleted:
            return None
        
        if name is not None:
            item.name = name
        if price is not None:
            item.price = price

        return item.model_copy(deep=True)
    
    def delete_item(self, item_id: int):
        item: Item = self._get_item(item_id)
        item.deleted = True
