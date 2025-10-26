from shop_api.schemas.cart import Cart, CartItem
from shop_api.storage.memory import _carts, _items


def compute_cart(cart_id: int) -> Cart:
    if cart_id not in _carts:
        raise KeyError
    bag = _carts[cart_id]
    items_out = []
    total = 0.0
    for iid, qty in bag.items():
        item = _items.get(iid)
        if item is None:
            name, available = "", False
        else:
            name, available = item.name, not item.deleted
        items_out.append(CartItem(id=iid, name=name, quantity=qty, available=available))
        if item and not item.deleted:
            total += item.price * qty
    return Cart(id=cart_id, items=items_out, price=total)