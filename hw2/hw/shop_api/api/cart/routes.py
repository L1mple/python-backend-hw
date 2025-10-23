from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from store.database import get_db
from store.queries import CartQueries, ItemQueries
from .contracts import CartResponse, CartCreateResponse

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_cart(db: Session = Depends(get_db)):
    cart = CartQueries.create_cart(db)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"id": cart.id},
        headers={"Location": f"/cart/{cart.id}"}
    )

@router.get("/{cart_id}", response_model=CartResponse)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    db_cart = CartQueries.get_cart(db, cart_id)
    if not db_cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    total_price = 0.0
    cart_items = []
    
    for cart_item in db_cart.items:
        item = cart_item.item
        available = not item.deleted
        total_price += item.price * cart_item.quantity
        
        cart_items.append({
            "id": item.id,
            "name": item.name,
            "quantity": cart_item.quantity,
            "available": available
        })
    
    return {
        "id": db_cart.id,
        "items": cart_items,
        "price": total_price
    }

@router.get("/", response_model=List[CartResponse])
def get_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db)
):
    carts = CartQueries.get_all_carts(db)
    
    result = []
    for db_cart in carts:
        total_price = 0.0
        total_quantity = 0
        cart_items = []
        
        for cart_item in db_cart.items:
            item = cart_item.item
            available = not item.deleted
            total_price += item.price * cart_item.quantity
            total_quantity += cart_item.quantity
            
            cart_items.append({
                "id": item.id,
                "name": item.name,
                "quantity": cart_item.quantity,
                "available": available
            })
        
        cart_data = {
            "id": db_cart.id,
            "items": cart_items,
            "price": total_price
        }
        
        # Применяем фильтры
        if min_price is not None and total_price < min_price:
            continue
        if max_price is not None and total_price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
            
        result.append(cart_data)
    
    # Применяем пагинацию после фильтрации
    return result[offset:offset + limit]

@router.post("/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = CartQueries.add_item_to_cart(db, cart_id, item_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart or item not found")
    return {"message": "Item added to cart"}
