from typing import Dict, Any

# in-memory хранилище
ITEMS: Dict[int, Dict[str, Any]] = {}
CARTS: Dict[int, Dict[str, Any]] = {}

item_id_seq: int = 1
cart_id_seq: int = 1


def next_item_id() -> int:
    global item_id_seq
    item_id = item_id_seq
    item_id_seq += 1
    return item_id


def next_cart_id() -> int:
    global cart_id_seq
    cart_id = cart_id_seq
    cart_id_seq += 1
    return cart_id


def compute_cart(cart: Dict[str, Any]) -> Dict[str, Any]:

    """Собирает корзину с пересчитанной ценой и items"""

    from .storage import ITEMS

    items_out = []
    total_price = 0.0
    for item_id, quantity in cart["items"].items():
        item = ITEMS.get(item_id)
        if not item:
            continue
        available = not item["deleted"]
        items_out.append(
            {
                "id": item_id,
                "name": item["name"],
                "quantity": quantity,
                "available": available,
            }
        )
        if available:
            total_price += item["price"] * quantity

    return {
        "id": cart["id"],
        "items": items_out,
        "price": total_price,
    }
