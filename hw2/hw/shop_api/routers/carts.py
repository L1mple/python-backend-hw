from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from ..factory import CartItem, CartResponse
from ..services.service_carts import CartService
from ..database import db


cart_service = CartService(db)

router = APIRouter(prefix="/cart", tags=["carts"])

@router.post("")
async def create_cart():
    return cart_service.create_cart()

@router.get("/{cart_id}", response_model=CartResponse)
async def get_item(cart_id: int):
    return cart_service.get_cart(cart_id)

@router.get("", response_model=List[CartResponse])
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0) 
):
    return cart_service.list_carts(offset, limit, min_price, max_price, min_quantity, max_quantity)

@router.post("/{cart_id}/add/{item_id}", response_model=CartResponse)
async def add_to_cart(cart_id: int, item_id: int):
    return cart_service.add_to_cart(cart_id, item_id)
