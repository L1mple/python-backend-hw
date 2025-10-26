from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response

from ..schemas import Cart
from ..storage import (
    add_to_cart as db_add_to_cart,
    cart_to_model as db_cart_to_model,
    create_cart as db_create_cart,
    list_carts as db_list_carts,
)


router = APIRouter(prefix="/cart")


def cart_to_model_or_404(cart_id: int) -> Cart:
    model = db_cart_to_model(cart_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    return model


@router.post("", status_code=201)
def create_cart(response: Response) -> dict:
    cid = db_create_cart()
    response.headers["Location"] = f"/cart/{cid}"
    return {"id": cid}


@router.get("/{cart_id}")
def get_cart(cart_id: int) -> Cart:
    return cart_to_model_or_404(cart_id)


@router.get("")
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    min_quantity: Optional[int] = Query(default=None, ge=0),
    max_quantity: Optional[int] = Query(default=None, ge=0),
) -> List[Cart]:
    return db_list_carts(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )


@router.post("/{cart_id}/add/{item_id}")
def add_to_cart(cart_id: int, item_id: int) -> Cart:
    try:
        model = db_add_to_cart(cart_id, item_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Item not found")
    if model is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    return model


