from typing import Optional, List

from store.queries.utils import id_generator
from store.queries.item import get_item_by_id, data_item
from store.models import (
    Cart,
    Item,
    CartItem
)



data_cart = dict[int, Cart]()
cart_id_generator = id_generator()



def add_cart() -> int:
    new_cart_id = next(cart_id_generator)
    data_cart[new_cart_id] = Cart(new_cart_id, [])
    return new_cart_id


def get_cart_by_id(id: int) -> Cart | None:
    if id not in data_cart:
        return None
    cart = data_cart[id]
    if cart.items:
        recalculate_cart(cart)
    return data_cart[id]


def recalculate_cart(cart: Cart):
    total = 0.0
    for item in cart.items:
        cart_item = get_item_by_id(item.id)
        print(cart_item)
        if cart_item and not cart_item.deleted:
            item.available = True
            total += cart_item.price * item.quantity
        else:
            item.available = False

    cart.price = total


def update_item_full(
        item_id: int,
        name: Optional[str] = None,
        price: Optional[float] = None,
        deleted: Optional[bool] = None,
) -> Item | None:
    if not item_id in data_item:
        return None

    if name:
        data_item[item_id].name = name

    if price:
        data_item[item_id].price = price

    if deleted is not None:
        data_item[item_id].deleted = deleted

    return data_item[item_id]


def update_item_partial(
        item_id: int,
        name: Optional[str] = None,
        price: Optional[float] = None
) -> Item | None:

    if item_id not in data_item:
        return None

    if name:
        data_item[item_id].name = name

    if price:
        data_item[item_id].price = price

    return data_item[item_id]


def list_carts(
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None
) -> List[Cart]:

    result = []
    for cart in data_cart.values():
        if cart.items:
            recalculate_cart(cart)
            total_quantity = sum(item.quantity for item in cart.items)

            if min_price is not None and cart.price < min_price:
                continue

            if max_price is not None and cart.price > max_price:
                continue

            if min_quantity is not None and total_quantity < min_quantity:
                continue

            if max_quantity is not None and total_quantity > max_quantity:
                continue

            result.append(cart)

    offset = offset or 0
    limit = limit or len(result)

    return result[offset:offset + limit]


def add_item_to_cart(
        cart_id: int,
        item_id: int
) -> Cart | None:

    if not cart_id in data_cart or \
        not item_id in data_item:
        return None

    cart = get_cart_by_id(cart_id)
    item = get_item_by_id(item_id)

    if item.deleted:
        return None

    added = False
    if cart.items:
        for cart_item in cart.items:
            if cart_item.id == item_id:
                added = True
                cart_item.quantity += 1
                break

    if not added:
        cart.items.append(
            CartItem(
                id=item_id,
                name=item.name,
                quantity=1,
                available=True
            )
        )

    return cart