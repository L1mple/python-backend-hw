from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..services.service_carts import CartService
from ..factory import CartResponse


router = APIRouter(prefix="/cart", tags=["carts"])

def get_cart_service(db: Session = Depends(get_db)) -> CartService:
    return CartService(db)

@router.post("")
async def create_cart(
    cart_service: CartService = Depends(get_cart_service)
):
    return cart_service.create_cart()

@router.get("/{cart_id}", response_model=CartResponse)
async def get_cart(
    cart_id: int,
    cart_service: CartService = Depends(get_cart_service)
):
    return cart_service.get_cart(cart_id)

@router.get("", response_model=List[CartResponse])
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    cart_service: CartService = Depends(get_cart_service)
):
    return cart_service.list_carts(offset, limit, min_price, max_price, min_quantity, max_quantity)

@router.post("/{cart_id}/add/{item_id}", response_model=CartResponse)
async def add_to_cart(cart_id: int,
                      item_id: int,
                      cart_service: CartService = Depends(get_cart_service)):
    return cart_service.add_to_cart(cart_id, item_id)
