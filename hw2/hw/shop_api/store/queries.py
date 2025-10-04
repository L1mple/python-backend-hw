from shop_api.store.models import Cart, Item, CartItem

_carts: list[Cart] = []
_items: list[Item] = []


def create_cart_record() -> Cart:
    cart = Cart(id=len(_carts))
    _carts.append(cart)
    return cart


def list_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None,
):
    min_price = min_price or -float("inf")
    max_price = max_price or float("inf")
    min_quantity = min_quantity or -float("inf")
    max_quantity = float('inf') if max_quantity is None else max_quantity
    return [
        _carts[i]
        for i in range(offset, min(offset + limit, len(_carts)))
        if (min_price <= _carts[i].price <= max_price)
        and (min_quantity <= len(_carts[i].items) <= max_quantity)
    ]


def list_items(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    show_deleted: bool = False,
) -> list[Item]:
    min_price = min_price or -float("inf")
    max_price = max_price or float("inf")
    return [
        _items[i]
        for i in range(offset, min(offset + limit, len(_items)))
        if (show_deleted or not _items[i].deleted)
        and min_price <= _items[i].price <= max_price
    ]


def add_cart_item(cart: Cart, item: Item) -> None:
    for cart_item in cart.items:
        if cart_item.id == item.id:
            cart_item.quantity += 1
            cart.price += item.price
            return
    cart.items.append(CartItem(id=item.id, name=item.name, quantity=1, available=not item.deleted))
    cart.price += item.price


def create_item_record(name: str, price: float) -> Item:
    item = Item(id=len(_items), name=name, price=price, deleted=False)
    _items.append(item)
    return item


def replace_item_record(item_id: int, name: str, price: float) -> None:
    _items[item_id].name = name
    _items[item_id].price = price
    _items[item_id].deleted = False


def patch_item_record(item_id: int, name: str | None, price: float | None) -> None:
    if name is not None:
        _items[item_id].name = name
    if price is not None:
        _items[item_id].price = price


def delete_item(item_id: int) -> None:
    _items[item_id].deleted = True
