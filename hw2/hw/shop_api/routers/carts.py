from fastapi import APIRouter, Query, Response
from typing import Dict, List, Optional

from ..models import Cart
from ..storage import create_cart, cart_view, add_to_cart, all_carts


router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("", status_code=201)
def post_cart(response: Response) -> Dict[str, int]:
    cid = create_cart()
    response.headers["Location"] = f"/cart/{cid}"
    return {"id": cid}


@router.get("/{cart_id}", response_model=Cart)
def get_cart(cart_id: int) -> Cart:
    return cart_view(cart_id)


@router.get("", response_model=List[Cart])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
) -> List[Cart]:

    carts: List[Cart] = []
    for cid in all_carts():
        cart = cart_view(cid)
        total_qty = sum(ci.quantity for ci in cart.items)
        if min_price is not None and cart.price < float(min_price):
            continue
        if max_price is not None and cart.price > float(max_price):
            continue
        if min_quantity is not None and total_qty < int(min_quantity):
            continue
        if max_quantity is not None and total_qty > int(max_quantity):
            continue
        carts.append(cart)
    return carts[offset: offset + limit]


@router.post("/{cart_id}/add/{item_id}", response_model=Cart)
def add(cart_id: int, item_id: int) -> Cart:
    add_to_cart(cart_id, item_id)
    return cart_view(cart_id)
