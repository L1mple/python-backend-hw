from fastapi import APIRouter, HTTPException, Query, Response
from typing import List, Optional
from ..schemas import Cart, CartItem
from ..storages import CartStorage, ItemStorage
from http import HTTPStatus

router = APIRouter(prefix="/cart", tags=["carts"])


@router.post("/", response_model=dict, status_code=HTTPStatus.CREATED)
def create_cart(response: Response):
    cart_id = CartStorage.create()
    response.headers["location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@router.get("/{cart_id}", response_model=Cart)
def get_cart(cart_id: int):
    cart = CartStorage.get(cart_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    return cart


@router.get("/", response_model=List[Cart])
def get_carts(
        offset: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        min_price: Optional[float] = Query(None, ge=0),
        max_price: Optional[float] = Query(None, ge=0),
        min_quantity: Optional[int] = Query(None, ge=0),
        max_quantity: Optional[int] = Query(None, ge=0)
):
    carts = CartStorage.get_all()

    # Apply filters
    filtered_carts = []
    for cart in carts:
        total_quantity = sum(item.quantity for item in cart.items)

        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        filtered_carts.append(cart)

    # Apply pagination
    return filtered_carts[offset:offset + limit]


@router.post("/{cart_id}/add/{item_id}", response_model=Cart)
def add_item_to_cart(cart_id: int, item_id: int):
    cart = CartStorage.get(cart_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")

    item = ItemStorage.get(item_id)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    # Check if item already in cart
    for cart_item in cart.items:
        if cart_item.id == item_id:
            cart_item.quantity += 1
            break
    else:
        # Item not in cart, add new
        cart_item = CartItem(
            id=item.id,
            name=item.name,
            quantity=1,
            available=not item.deleted
        )
        cart.items.append(cart_item)

    # Recalculate total price
    cart.price = sum(
        item.price * cart_item.quantity
        for cart_item in cart.items
        if (item := ItemStorage.get(cart_item.id)) and not item.deleted
    )

    CartStorage.update(cart)
    return cart
