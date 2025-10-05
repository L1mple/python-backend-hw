from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response

from ..schemas import Cart, CartItem
from ..storage import carts_items, items_by_id, next_cart_id


router = APIRouter(prefix="/cart")


def compute_cart_price(cart_map: dict[int, int]) -> float:
    total = 0.0
    for item_id, quantity in cart_map.items():
        item = items_by_id.get(item_id)
        if item is None or item.deleted:
            continue
        total += item.price * quantity
    return total


def cart_to_model(cart_id: int) -> Cart:
    cart_map = carts_items.get(cart_id)
    if cart_map is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    items = [CartItem(id=iid, quantity=qty) for iid, qty in cart_map.items()]
    return Cart(id=cart_id, items=items, price=compute_cart_price(cart_map))


@router.post("", status_code=201)
def create_cart(response: Response) -> dict:
    global next_cart_id
    cid = next_cart_id
    carts_items[cid] = {}
    response.headers["Location"] = f"/cart/{cid}"
    next_cart_id += 1
    return {"id": cid}


@router.get("/{cart_id}")
def get_cart(cart_id: int) -> Cart:
    return cart_to_model(cart_id)


@router.get("")
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    min_quantity: Optional[int] = Query(default=None, ge=0),
    max_quantity: Optional[int] = Query(default=None, ge=0),
) -> List[Cart]:
    carts = [cart_to_model(cid) for cid in carts_items.keys()]

    if min_price is not None:
        carts = [c for c in carts if c.price >= min_price]
    if max_price is not None:
        carts = [c for c in carts if c.price <= max_price]

    def qsum(c: Cart) -> int:
        return sum(ci.quantity for ci in c.items)

    if min_quantity is not None:
        carts = [c for c in carts if qsum(c) >= min_quantity]
    if max_quantity is not None:
        carts = [c for c in carts if qsum(c) <= max_quantity]

    return carts[offset : offset + limit]


@router.post("/{cart_id}/add/{item_id}")
def add_to_cart(cart_id: int, item_id: int) -> Cart:
    cart = carts_items.get(cart_id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    item = items_by_id.get(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    cart[item_id] = cart.get(item_id, 0) + 1
    return cart_to_model(cart_id)


