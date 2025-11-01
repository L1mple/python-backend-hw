from typing import List, Optional

from shop_api.models import CartItem, Cart, Item


carts: List[Cart] = []

class CartNotFoundException(Exception):
    pass

class CartsRepository:
    def create_cart() -> Cart:
        cart_id = len(carts)
        cart = Cart(id=cart_id, items=[], price=0.0)
        carts.append(cart)
        return cart.model_copy(deep=True)
    
    def get_cart(cart_id: int) -> Cart:
        if cart_id >= len(carts):
            raise CartNotFoundException()
        return carts[cart_id].model_copy(deep=True)
    
    def get_carts(offset: int, limit: int) -> List[Cart]:
        return [cart.model_copy(deep=True) for cart in carts[offset:offset+limit]]
    
    def update_cart(new_cart: Cart):
        if new_cart.id > len(carts):
            raise CartNotFoundException()
        carts[new_cart.id] = new_cart


items: List[Item] = []

class ItemNotFoundException(Exception):
    pass

class ItemsRepository:
    def create_item(name: str, price: float) -> Item:
        item_id = len(items)
        item = Item(id=item_id, name=name, price=price, deleted=False)
        items.append(item)
        return item.model_copy(deep=True)
    
    def _get_item(item_id: int) -> Item:
        if item_id >= len(items):
            raise ItemNotFoundException()
        return items[item_id]
    
    def get_item(item_id: int) -> Item:
        item: Item = ItemsRepository._get_item(item_id)
        if item.deleted:
            raise ItemNotFoundException()

        return item.model_copy(deep=True)

    def get_items(offset: int, limit: int) -> List[Item]:
        return [item.model_copy(deep=True) for item in items[offset:offset+limit]]
    
    def replace_item(item_id: int, name: str, price: float) -> Item:
        if item_id >= len(items):
            raise ItemNotFoundException()

        item = Item(id=item_id, name=name, price=price, deleted=False)
        items[item_id] = item
        return item.model_copy(deep=True)
    
    def update_item(item_id: int, name: Optional[str], price: Optional[float]) -> Optional[Item]:
        item: Item = ItemsRepository._get_item(item_id)
        
        if item.deleted:
            return None
        
        if name is not None:
            item.name = name
        if price is not None:
            item.price = price

        return item.model_copy(deep=True)
    
    def delete_item(item_id: int):
        item: Item = ItemsRepository._get_item(item_id)
        item.deleted = True
