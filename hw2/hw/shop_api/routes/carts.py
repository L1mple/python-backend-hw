from fastapi import APIRouter, HTTPException, Query, status, Response
from typing import List, Optional
from ..models import Cart, CartCreateResponse
from ..storage import storage

router = APIRouter(prefix="/cart", tags=["carts"])


@router.post("/", response_model=CartCreateResponse, status_code=status.HTTP_201_CREATED)
def create_cart(response: Response):
    cart_id = storage.create_cart()
    response.headers["Location"] = f"/cart/{cart_id}"
    return CartCreateResponse(id=cart_id)


@router.get("/{cart_id}", response_model=Cart)
def get_cart(cart_id: int):
    cart = storage.get_cart(cart_id)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    return cart


@router.get("/", response_model=List[Cart])
def list_carts(
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=1),
        min_price: Optional[float] = Query(None, ge=0),
        max_price: Optional[float] = Query(None, ge=0),
        min_quantity: Optional[int] = Query(None, ge=0),
        max_quantity: Optional[int] = Query(None, ge=0)
):
    def cart_filter(cart: Cart) -> bool:
        total_quantity = sum(item.quantity for item in cart.items)
        return all([
            min_price is None or cart.price >= min_price,
            max_price is None or cart.price <= max_price,
            min_quantity is None or total_quantity >= min_quantity,
            max_quantity is None or total_quantity <= max_quantity
        ])

    filtered_carts = list(filter(cart_filter, storage.carts.values()))
    return filtered_carts[offset:offset + limit]


@router.post("/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int):
    success = storage.add_item_to_cart(cart_id, item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cart or item not found")
    return {"message": "Item added to cart"}