from typing import Optional, List, Dict
from shop_api.models import (
    Cart,
    Item,
    CartItem,
    CartFilterParams,
    ItemFilterParams,
    NotModifiedError,
    NotFoundError
)


class DB:
    def __init__(self):
        print('---Инициализация соединения с БД---')
        self.carts_db: Dict[int, Cart] = {}
        self.items_db: Dict[int, Item] = {}
        
    def _generate_id(self, db: dict) -> int:
        cur_max_id = max(db.keys() or [0])
        return cur_max_id + 1
    
    def _calculate_all_items_in_cart_price(self, cart_id: int) -> float:
        return sum([item.quantity * self.items_db[item.id].price for item in self.carts_db[cart_id].items])

    def create_cart(self) -> Cart:
        new_id = self._generate_id(self.carts_db)
        new_cart = Cart(id=new_id)
        self.carts_db[new_id] = new_cart
        return new_cart
    
    def get_cart_by_id(self, cart_id: int) -> Optional[Cart]:
        return self.carts_db.get(cart_id)
    
    def get_carts(self, params: CartFilterParams) -> List[Cart]:
        carts = list(self.carts_db.values())
        if params.min_price is not None:
            carts = [cart for cart in carts if cart.price >= params.min_price]
        if params.max_price is not None:
            carts = [cart for cart in carts if cart.price <= params.max_price]
        if params.min_quantity is not None:
            carts = [cart for cart in carts if sum(item.quantity for item in cart.items) >= params.min_quantity]
        if params.max_quantity is not None:
            carts = [cart for cart in carts if sum(item.quantity for item in cart.items) <= params.max_quantity]
        if params.offset:
            carts = carts[params.offset:]
        if params.limit:
            carts = carts[:params.limit]
        return carts
    
    def add_item_to_cart(self, cart_id: int, item_id: int) -> bool:
        if not cart_id in self.carts_db or not item_id in self.items_db:
            raise NotFoundError(detail="Корзина и/или товар не найдены")
        
        item: Item = self.items_db[item_id]
        cart: Cart = self.carts_db[cart_id]
        current_items_in_cart: List[CartItem] = [cart_item for cart_item in cart.items if cart_item.id == item_id]
        item_available = not item.deleted
        if len(current_items_in_cart) == 1:
            item_in_cart: CartItem = current_items_in_cart[0]
            item_in_cart.quantity += 1
            item_in_cart.available = item_available
        else:
            item_in_cart = CartItem(id=item_id, name=item.name, quantity=1, available=item_available)

        new_item_list: List[CartItem] = [cart_item for cart_item in cart.items if cart_item.id != item_id]
        new_item_list.append(item_in_cart)
        self.carts_db[cart_id].items = new_item_list
        self.carts_db[cart_id].price = self._calculate_all_items_in_cart_price(cart_id)
        return True
    
    def create_item(self, name: str, price: float) -> Item:
        new_id = self._generate_id(self.items_db)
        new_item = Item(id=new_id, name=name, price=price)
        self.items_db[new_id] = new_item
        return new_item

    def get_item_by_id(self, item_id: int) -> Optional[Item]:
        item = self.items_db.get(item_id)
        if not item or item.deleted:
            return None
        return item
    
    def get_items(self, params: ItemFilterParams) -> List[Item]:
        items = list(self.items_db.values())
        if not params.show_deleted:
            items = [item for item in items if not item.deleted]
        if params.min_price is not None:
            items = [item for item in items if item.price >= params.min_price]
        if params.max_price is not None:
            items = [item for item in items if item.price <= params.max_price]
        if params.offset:
            items = items[params.offset:]
        if params.limit:
            items = items[:params.limit]
        return items

    def replace_item(self, item_id: int, new_name: str, new_price: float) -> Item:
        item = self.items_db.get(item_id)
        if not item:
            raise NotFoundError("Товар не найден")
        item.name = new_name
        item.price = new_price
        self.items_db[item_id] = item
        return item

    def edit_item(self, item_id: int, new_name: Optional[str] = None, new_price: Optional[str] = None) -> Item:
        item = self.items_db.get(item_id)

        if not item:
            raise NotFoundError("Товар не найден")

        if item.deleted:
            raise NotModifiedError("Товар удален, его невозможно изменить")
        
        if new_name:
            item.name = new_name
        if new_price:
            item.price = new_price

        self.items_db[item_id] = item
        return item
    
    def delete_item(self, item_id: int) -> bool:
        item = self.items_db.get(item_id)
        if not item:
            raise NotFoundError("Товар не найден")
        
        item.deleted = True
        self.items_db[item_id] = item
        return True
    
    def close(self):
        print('---Закрытие соединения с БД---')
        pass
