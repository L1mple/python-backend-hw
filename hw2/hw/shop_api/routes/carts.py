from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Response

from ..models import CartResponse, CartItemResponse
from ..storage import storage

router = APIRouter(prefix="/cart", tags=["carts"])


@router.post("", status_code=201)
def create_cart(response: Response):
    cart_id = storage.create_cart()
    response.headers["Location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@router.get("/{cart_id}", response_model=CartResponse)
def get_cart(cart_id: int):
    cart = storage.get_cart_by_id(cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    cart_items = []
    for item_id, quantity in cart.get("items", {}).items():
        item = storage.get_item_by_id(int(item_id))
        if item:
            cart_items.append(CartItemResponse(
                id=item["id"],
                name=item["name"],
                quantity=quantity,
                available=not item.get("deleted", False)
            ))
    
    total_price = storage.calculate_cart_price(cart)
    
    return CartResponse(
        id=cart["id"],
        items=cart_items,
        price=total_price
    )


@router.get("", response_model=List[CartResponse])
def get_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0)
):
    carts = storage.get_all_carts()
    
    if min_price is not None or max_price is not None:
        filtered_carts = []
        for cart in carts:
            cart_price = storage.calculate_cart_price(cart)
            if min_price is not None and cart_price < min_price:
                continue
            if max_price is not None and cart_price > max_price:
                continue
            filtered_carts.append(cart)
        carts = filtered_carts
    
    if min_quantity is not None or max_quantity is not None:
        filtered_carts = []
        for cart in carts:
            total_quantity = sum(cart.get("items", {}).values())
            if min_quantity is not None and total_quantity < min_quantity:
                continue
            if max_quantity is not None and total_quantity > max_quantity:
                continue
            filtered_carts.append(cart)
        carts = filtered_carts
    
    carts = carts[offset:offset + limit]
    
    result = []
    for cart in carts:
        cart_items = []
        for item_id, quantity in cart.get("items", {}).items():
            item = storage.get_item_by_id(int(item_id))
            if item:
                cart_items.append(CartItemResponse(
                    id=item["id"],
                    name=item["name"],
                    quantity=quantity,
                    available=not item.get("deleted", False)
                ))
        
        total_price = storage.calculate_cart_price(cart)
        
        result.append(CartResponse(
            id=cart["id"],
            items=cart_items,
            price=total_price
        ))
    
    return result


@router.post("/{cart_id}/add/{item_id}", status_code=200)
def add_item_to_cart(cart_id: int, item_id: int):
    cart = storage.get_cart_by_id(cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    item = storage.get_item_by_id(item_id)
    if not item or item.get("deleted", False):
        raise HTTPException(status_code=404, detail="Item not found")
    
    storage.add_item_to_cart(cart_id, item_id)
    return {"message": "Item added to cart"}
