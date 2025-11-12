from store.models import Item, Cart, CartItem

_items: list[Item] = []
_carts: list[Cart] = []
_next_item_id = 1
_next_cart_id = 1


def create_item(name: str, price: float) -> Item:
    global _next_item_id
    item = Item(id=_next_item_id, name=name, price=price, deleted=False)
    _items.append(item)
    _next_item_id += 1
    return item


def get_item(item_id: int):
    for i in _items:
        if i.id == item_id:
            return i
    return None


def list_items():
    return _items


def replace_item(item_id: int, new_item: Item):
    for i, item in enumerate(_items):
        if item.id == item_id:
            _items[i] = new_item
            return new_item
    return None


def patch_item(item_id: int, data: dict):
    item = get_item(item_id)
    if not item:
        return None
    for k, v in data.items():
        setattr(item, k, v)
    return item


def delete_item(item_id: int):
    item = get_item(item_id)
    if not item:
        return False
    item.deleted = True
    return True

def create_cart() -> Cart:
    global _next_cart_id
    cart = Cart(id=_next_cart_id, items=[], price=0.0)
    _carts.append(cart)
    _next_cart_id += 1
    return cart


def get_cart(cart_id: int):
    for c in _carts:
        if c.id == cart_id:
            return c
    return None


def list_carts():
    return _carts


def add_to_cart(cart_id: int, item_id: int):
    cart = get_cart(cart_id)
    item = get_item(item_id)
    if not cart or not item:
        return None

    for ci in cart.items:
        if ci.id == item_id:
            ci.quantity += 1
            break
    else:
        cart.items.append(CartItem(id=item.id, name=item.name, quantity=1, available=True))

    cart.price = sum(ci.quantity * get_item(ci.id).price for ci in cart.items)
    return cart
