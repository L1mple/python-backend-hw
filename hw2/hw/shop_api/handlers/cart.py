from http import HTTPStatus
from typing import List
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from shop_api.models.cart import CartLineOut, CartOut
from shop_api.models.item import ItemRecord
from shop_api.storage.psql_sqlalchemy import (
    get_store,
    create_cart as psql_create_cart,
    get_cart as psql_get_cart,
    list_carts as psql_list_carts,
    add_to_cart as psql_add_to_cart,
    list_items as psql_list_items,
    get_items_by_ids as psql_get_items_by_ids,
)


router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("")
async def create_cart(deps=Depends(get_store)):
    cid = psql_create_cart()
    content = {"id": cid}
    headers = {"Location": f"/cart/{cid}"}
    return JSONResponse(
        content=content, headers=headers, status_code=HTTPStatus.CREATED
    )


@router.get("/{cart_id}", response_model=CartOut)
async def get_cart(cart_id: int, deps=Depends(get_store)):
    cart = psql_get_cart(cart_id)
    if cart is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="cart not found")
    cart = {int(k): int(v) for k, v in cart.items()} if cart else {}
    item_ids = list(cart.keys()) if cart else []
    items_list = psql_get_items_by_ids(item_ids) if item_ids else []
    items = {
        int(i["id"]): ItemRecord(
            name=i["name"],
            price=i["price"],
            description=i.get("description"),
            deleted=i.get("deleted", False),
        )
        for i in items_list
    }
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
    rows = psql_list_carts()
    items_list = psql_list_items(show_deleted=False)
    items = {
        i["id"]: ItemRecord(
            name=i["name"],
            price=i["price"],
            description=i["description"],
            deleted=i["deleted"],
        )
        for i in items_list
    }
    outs = []
    for r in rows:
        cid = r["id"] if isinstance(r, dict) else r["id"]
        cart = r.get("cart") if isinstance(r, dict) else r["cart"]
        cart = (
            {
                int(k): int(v)
                for k, v in (cart.items() if isinstance(cart, dict) else cart)
            }
            if cart
            else {}
        )
        resp = build_cart_response(cid, cart, items)
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
    try:
        cart = psql_add_to_cart(cart_id, item_id)
    except ValueError as e:
        raise HTTPException(HTTPStatus.BAD_REQUEST, str(e))
    if cart is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, "cart or item not found")

    items_list = psql_list_items(show_deleted=False)
    items = {
        i["id"]: ItemRecord(
            name=i["name"],
            price=i["price"],
            description=i["description"],
            deleted=i["deleted"],
        )
        for i in items_list
    }
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
