from http import HTTPStatus
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from shop_api.models.cart import CartLineOut, CartOut
from shop_api.models.item import ItemRecord
from shop_api.storage.in_mem import get_store

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("")
async def create_cart(deps=Depends(get_store)):
    items, carts, lock = deps
    async with lock:
        cart_id = len(carts) + 1
        carts[cart_id] = {}

        content = {"id": cart_id}
        headers = {"Location": f"/cart/{cart_id}"}
        return JSONResponse(
            content=content, headers=headers, status_code=HTTPStatus.CREATED
        )


@router.get("/{cart_id}", response_model=CartOut)
async def get_cart(cart_id: int, deps=Depends(get_store)):
    items, carts, lock = deps
    async with lock:
        cart = carts.get(cart_id)
        if cart is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND, detail="cart not found"
            )

        return build_cart_response(cart_id, cart, items)


@router.get("", response_model=List[CartOut])
async def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    min_quantity: int | None = Query(None, ge=0),
    max_quantity: int | None = Query(None, ge=0),
    deps=Depends(get_store),
):
    items, carts, lock = deps
    async with lock:
        outs: list[CartOut] = []

        for cid, cmap in carts.items():
            resp = build_cart_response(cid, cmap, items)
            if min_price is not None and resp.price < min_price:
                continue
            if max_price is not None and resp.price > max_price:
                continue
            if min_quantity is not None and resp.quantity < min_quantity:
                continue
            if max_quantity is not None and resp.quantity > max_quantity:
                continue
            outs.append(resp)
        return outs[offset : offset + limit]


@router.post("/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int, deps=Depends(get_store)):

    items, carts, lock = deps
    async with lock:
        cart = carts.get(cart_id)
        if cart is None:
            raise HTTPException(HTTPStatus.NOT_FOUND, "cart not found")
        rec: None | ItemRecord = items.get(item_id)
        if not rec:
            raise HTTPException(HTTPStatus.NOT_FOUND, "item not found")
        if rec.deleted:
            raise HTTPException(HTTPStatus.BAD_REQUEST, "item not available")

        cart[item_id] = cart.get(item_id, 0) + 1
        return build_cart_response(cart_id, cart, items)


def build_cart_response(
    cart_id: int, cart: dict[int, int], items: dict[int, ItemRecord]
) -> CartOut:
    lines: list[CartLineOut] = []
    total_price = 0.0
    total_quantity = 0
    for item_id, quantity in cart.items():
        rec = items.get(item_id)
        if not rec or rec.deleted:
            continue
        line_total = rec.price * quantity
        lines.append(
            CartLineOut(
                id=item_id,
                quantity=quantity,
            )
        )
        total_price += line_total
        total_quantity += quantity
    return CartOut(id=cart_id, items=lines, price=total_price, quantity=total_quantity)
