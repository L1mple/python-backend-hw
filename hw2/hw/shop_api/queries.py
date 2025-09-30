import itertools

from hw2.hw.shop_api.models import (BaseItem, Cart, CartFilters, CartItem,
                                    Item, ItemFilters, PatchItem)

_carts = dict[int, Cart]()
_items = dict[int, Item]()
_carts_items_quantity_map = dict[int, dict[int, int]]()
id_generator_cart = itertools.count(start=1, step=1)
id_generator_item = itertools.count(start=1, step=1)


def create_empty_cart() -> Cart:
    _id = next(id_generator_cart)
    _carts[_id] = Cart(id=_id, items=[], price=0.0)
    _carts_items_quantity_map[_id] = {}
    return _carts[_id]


def generate_cart_items(cart_id: int) -> (list[CartItem], float):
    cart_items: list[CartItem] = []
    price: float = 0.0
    for item_id, item_quantity in _carts_items_quantity_map[cart_id].items():
        cart_item = CartItem(id=item_id,
                             name=_items.get(item_id).name,
                             quantity=item_quantity,
                             available=not _items.get(item_id).deleted)
        cart_items.append(cart_item)
        price += _items.get(cart_item.id).price * item_quantity
    return cart_items, price


def get_cart_by_id(cart_id: int) -> Cart | None:
    cart = _carts.get(cart_id)
    if cart and len(_carts_items_quantity_map[cart_id]) > 0:
        cart.items, cart.price = generate_cart_items(cart_id)
    return cart


def add_item(item: BaseItem) -> Item:
    _id = next(id_generator_item)
    _items[_id] = Item(id=_id, name=item.name, price=item.price, deleted=False)
    return _items[_id]


def get_item_by_id(item_id: int) -> Item | None:
    item = _items.get(item_id)
    return item


def add_to_cart(cart_id: int, item_id: int) -> Cart | None:
    cart = _carts.get(cart_id)
    item = _items.get(item_id)
    if not cart or not item:
        return None
    _carts_items_quantity_map[cart_id][item_id] = _carts_items_quantity_map[cart_id].get(item_id, 0) + 1
    cart.items, cart.price = generate_cart_items(cart_id)
    return cart


def get_carts_filtered(filters: CartFilters) -> list[Cart]:
    carts = list(_carts.values())

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

    carts_filtered = list(filter(matcher, carts))[filters.offset:filters.offset + filters.limit]
    return carts_filtered


def get_items_filtered(filters: ItemFilters) -> list[Item]:
    items = list(_items.values())

    def matcher(item: Item) -> bool:
        if filters.max_price is not None and item.price > filters.max_price:
            return False
        if filters.min_price is not None and item.price < filters.min_price:
            return False
        if not filters.show_deleted and item.deleted:
            return False

    items_filtered = list(filter(matcher, items))[filters.offset:filters.offset + filters.limit]
    return items_filtered


def delete_item_by_id(item_id: int) -> Item | None:
    item = _items.get(item_id)
    if not item:
        return None
    item.deleted = True
    return item


def patch_item_query(item_id: int, new_fields: PatchItem) -> Item | None:
    item = _items.get(item_id)
    if not item.deleted and new_fields.name:
        item.name = new_fields.name
    if not item.deleted and new_fields.price:
        item.price = new_fields.price

    return item


def put_item_query(item_id: int, new_fields: BaseItem) -> Item:
    item = _items.get(item_id)
    item.name, item.price = new_fields.name, new_fields.price

    return item
