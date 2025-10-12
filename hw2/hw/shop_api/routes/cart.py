from fastapi import APIRouter, Query, HTTPException, Response
from typing import Optional
from ..db import carts_db, items_db
from ..models.cart import Cart, CartItem

router = APIRouter(prefix='/cart')


@router.get('/{id}')
def get_cart(id: int):
    if id not in carts_db:
        raise HTTPException(status_code=404, detail="Not found")
    return carts_db[id]


@router.get('/')
def get_carts(
        limit: Optional[int] = Query(default=10, ge=1),
        offset: Optional[int] = Query(default=0, ge=0),
        min_price: Optional[float] = Query(default=None, ge=0),
        max_price: Optional[float] = Query(default=None, ge=0),
        min_quantity: Optional[int] = Query(default=None, ge=0),
        max_quantity: Optional[int] = Query(default=None, ge=0)
):
    carts = carts_db.values()
    if min_price is not None:
        carts = filter(lambda cart: cart.price >= min_price, carts)
    if max_price is not None:
        carts = filter(lambda cart: cart.price <= max_price, carts)
    if min_quantity is not None:
        carts = filter(lambda cart: sum(item.quantity for item in cart.items) >= min_quantity, carts)
    if max_quantity is not None:
        carts = filter(lambda cart: sum(item.quantity for item in cart.items) <= max_quantity, carts)
    return list(carts)[offset:offset + limit]


@router.post('/', status_code=201)
def create_cart(response: Response):
    cart = Cart(id=len(carts_db), items=[], price=0.0)
    carts_db[cart.id] = cart
    response.headers["location"] = f"/cart/{cart.id}"
    return cart


@router.post('/{cart_id}/add/{item_id}')
def add_item_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=404, detail="Cart not found")
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    if items_db[item_id].deleted:
        raise HTTPException(status_code=404, detail="Item not found")

    cart = carts_db[cart_id]
    item = items_db[item_id]

    existing = None
    for cart_item in cart.items:
        if cart_item.id == item_id:
            existing = cart_item
            break

    if existing:
        existing.quantity += 1
    else:
        cart.items.append(CartItem(
            id=item_id,
            name=item.name,
            quantity=1,
            available=not item.deleted
        ))

    cart.price = 0
    for item in cart.items:
        if item.id in items_db and not items_db[item.id].deleted:
            cart.price += items_db[item.id].price * item.quantity

    return cart
