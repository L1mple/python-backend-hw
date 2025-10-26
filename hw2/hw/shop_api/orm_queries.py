from shop_api.models import (BaseItem, Cart, CartFilters, CartItem, Item,
                             ItemFilters, PatchItem)
from shop_api.orm_models import Carts, CartsItems, Items
from sqlalchemy.orm import Session


def create_empty_cart(sess: Session) -> Cart:
    cart = Carts()
    sess.add(cart)
    sess.commit()

    return Cart(id=cart.id, items=cart.carts_items, price=0)

def generate_cart_items(cart: type[Carts]) -> (list[CartItem], float):
    items: list[CartItem] = []
    price: float = 0
    for i in cart.carts_items:
        items.append(
            CartItem(id=i.item.id, name=i.item.name, quantity=i.quantity, available=not i.item.deleted)
        )
        price += i.item.price * i.quantity
    return items, price

def get_cart_by_id(cart_id: int, sess: Session) -> Cart | None:
    cart = sess.get(Carts, cart_id)
    if cart:
        items, price = generate_cart_items(cart)
        return Cart(id=cart.id, items=items, price=price)
    return None

def add_item(item: BaseItem, sess: Session) -> Item:
    item_db = Items(name=item.name, price=item.price)
    sess.add(item_db)
    sess.commit()

    return Item(id=item_db.id, name=item_db.name, price=item_db.price, deleted=item_db.deleted)

def add_to_cart(cart_id: int, item_id: int, sess: Session) -> Cart | None:
    cart = sess.get(Carts, cart_id)
    item = sess.get(Items, item_id)
    if not cart or not item:
        return None

    exists = False
    for i in cart.carts_items:
        if i.item.id == item_id:
            i.quantity += 1
            exists = True
    if not exists:
        cart_new_item = CartsItems(cart_id=cart_id, item_id=item_id, quantity=1)
        sess.add(cart_new_item)
    sess.commit()

    return get_cart_by_id(cart_id, sess)

def get_item_by_id(item_id: int, sess: Session) -> Item | None:
    item = sess.get(Items, item_id)
    if item:
        return Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted)
    return None

def get_carts_filtered(filters: CartFilters, sess: Session) -> list[Cart]:
    all_carts = sess.query(Carts).all()
    result = []

    def matcher(cart: Cart) -> bool:
        if filters.max_price is not None and cart.price > filters.max_price:
            return False
        if filters.min_price is not None and cart.price < filters.min_price:
            return False
        if filters.max_quantity is not None and (sum([i.quantity for i in cart.items]) > filters.max_quantity):
            return False
        if filters.min_quantity is not None and (sum([i.quantity for i in cart.items]) < filters.min_quantity):
            return False
        return True
    for cart in all_carts[filters.offset:filters.offset + filters.limit]:
        items, price = generate_cart_items(cart)
        if matcher(Cart(id=cart.id, items=items, price=price)):
             result.append(Cart(id=cart.id, items=items, price=price))

    return result

def get_items_filtered(filters: ItemFilters, sess: Session) -> list[Item]:
    all_items = sess.query(Items).all()
    result = []

    def matcher(item: Item) -> bool:
        if filters.max_price is not None and item.price > filters.max_price:
            return False
        if filters.min_price is not None and item.price < filters.min_price:
            return False
        if not filters.show_deleted and item.deleted:
            return False

    for item_db in all_items[filters.offset:filters.offset + filters.limit]:
        if matcher(Item(id=item_db.id, name=item_db.name, price=item_db.price, deleted=item_db.deleted)):
            result.append(Item(id=item_db.id, name=item_db.name, price=item_db.price, deleted=item_db.deleted))

    return result

def delete_item_by_id(item_id: int, sess: Session) -> Item | None:
    item = sess.get(Items, item_id)
    if item:
        item.deleted = True
        sess.commit()
        return Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted)
    return None

def patch_item_query(item_id: int, new_fields: PatchItem, sess: Session) -> Item | None:
    item = sess.get(Items, item_id)
    if not item:
        return None
    if not item.deleted and new_fields.name:
        item.name = new_fields.name
    if not item.deleted and new_fields.price:
        item.price = new_fields.price
    sess.commit()
    return Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted)

def put_item_query(item_id: int, new_fields: BaseItem, sess: Session) -> Item:
    item = sess.get(Items, item_id)
    item.name, item.price = new_fields.name, new_fields.price

    return Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted)
