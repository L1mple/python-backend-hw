from __future__ import annotations
from http import HTTPStatus
from fastapi import APIRouter, HTTPException, Path, Query, Response

from shop_api.core.models import Cart, CartItem
from shop_api.core.schemas import CartOut, CartOutItem
from shop_api.core.store import store

router = APIRouter(tags=["carts"])

def _get_cart_or_404(cart_id: int) -> Cart:
    cart = store.get_cart(cart_id)
    if cart is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return cart

@router.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response):
    cart_id = store.next_cart_id()
    cart = Cart(id=cart_id, items=[])
    store.carts[cart_id] = cart
    response.headers["Location"] = f"/cart/{cart_id}"
    return {"id": cart_id}

@router.get("/cart/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int = Path(ge=1)):
    cart = _get_cart_or_404(cart_id)
    items_out: list[CartOutItem] = []

    for cart_item in cart.items:
        item = store.items.get(cart_item.id)
        if item is not None:
            items_out.append(
                CartOutItem(
                    id=item.id,
                    name=item.name,
                    quantity=cart_item.quantity,
                    available=not item.deleted,
                )
            )
        else:
            items_out.append(
                CartOutItem(
                    id=cart_item.id,
                    name="Unknown",
                    quantity=cart_item.quantity,
                    available=False,
                )
            )

    price = cart.total_price(store.items)
    return CartOut(id=cart.id, items=items_out, price=price)

@router.post("/cart/{cart_id}/add/{item_id}", status_code=HTTPStatus.OK)
def add_item_to_cart(cart_id: int = Path(ge=1), item_id: int = Path(ge=1)):
    cart = _get_cart_or_404(cart_id)
    item = store.items.get(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    for cart_item in cart.items:
        if cart_item.id == item_id:
            cart_item.quantity += 1
            break
    else:
        cart.items.append(CartItem(id=item_id, quantity=1))

    store.carts[cart_id] = cart
    return {"status": "ok"}

@router.get("/cart", response_model=list[CartOut])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_quantity: int | None = Query(default=None, ge=0),
    max_quantity: int | None = Query(default=None, ge=0),
):
    carts = list(store.carts.values())
    prepared: list[CartOut] = []

    for cart in carts:
        items_out: list[CartOutItem] = []
        for cart_item in cart.items:
            item = store.items.get(cart_item.id)
            if item is not None:
                items_out.append(
                    CartOutItem(
                        id=item.id,
                        name=item.name,
                        quantity=cart_item.quantity,
                        available=not item.deleted,
                    )
                )
            else:
                items_out.append(
                    CartOutItem(
                        id=cart_item.id,
                        name="Unknown",
                        quantity=cart_item.quantity,
                        available=False,
                    )
                )

        price = cart.total_price(store.items)
        prepared.append(CartOut(id=cart.id, items=items_out, price=price))

    if min_price is not None:
        prepared = [c for c in prepared if c.price >= min_price]
    if max_price is not None:
        prepared = [c for c in prepared if c.price <= max_price]

    def sum_quantity(c: CartOut) -> int:
        return sum(i.quantity for i in c.items)

    if min_quantity is not None:
        prepared = [c for c in prepared if sum_quantity(c) >= min_quantity]
    if max_quantity is not None:
        prepared = [c for c in prepared if sum_quantity(c) <= max_quantity]

    return prepared[offset : offset + limit]
