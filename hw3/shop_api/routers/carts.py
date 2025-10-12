from fastapi import APIRouter, HTTPException, Query, Path, Response
from shop_api.schemas.cart import Cart
from shop_api.utils.cart_utils import compute_cart
from shop_api.metrics import carts_created_counter
from shop_api.storage.memory import _carts, _items, _lock, _next_cart_id
from typing import Optional, List


router = APIRouter(prefix="/cart", tags=["carts"])

@router.post("/", status_code=201)
def create_cart(response: Response):
    global _next_cart_id
    with _lock:
        cid = _next_cart_id
        _next_cart_id += 1
        _carts[cid] = {}
    response.headers["Location"] = f"/cart/{cid}"
    carts_created_counter.inc()
    return {"id": cid}

@router.get("/{id}", response_model=Cart)
def get_cart(id: int = Path(..., gt=0)):
    try:
        return compute_cart(id)
    except KeyError:
        raise HTTPException(status_code=404, detail="cart not found")

@router.get("/", response_model=List[Cart])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    carts = []
    for cid in sorted(_carts.keys()):
        cart = compute_cart(cid)
        total_qty = sum(i.quantity for i in cart.items)
        if min_quantity is not None and total_qty < min_quantity:
            continue
        if max_quantity is not None and total_qty > max_quantity:
            continue
        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue
        carts.append(cart)
    return carts[offset: offset + limit]

@router.post("/{cart_id}/add/{item_id}", response_model=Cart)
def add_item(cart_id: int, item_id: int):
    if cart_id not in _carts:
        raise HTTPException(status_code=404, detail="cart not found")
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="item not found")
    _carts[cart_id][item_id] = _carts[cart_id].get(item_id, 0) + 1
    return compute_cart(cart_id)
