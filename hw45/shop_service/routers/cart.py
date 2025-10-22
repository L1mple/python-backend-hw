from http import HTTPStatus
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import NonNegativeInt, PositiveInt
from sqlalchemy.orm import Session

from db.utils import get_db
from db.cart import CartService, SqlAlchemyCartRepository
from db.item import SqlAlchemyItemRepository
from shop_service.schemas import Cart

from shop_service import data_storage


router = APIRouter(
    prefix="/cart",
    tags=["cart"],
)

@router.post("/")
async def create_cart(db: Session = Depends(get_db)):
    cart_service = CartService(SqlAlchemyCartRepository(db), SqlAlchemyItemRepository(db))
    
    cart = cart_service.create_cart()
    return JSONResponse(
        {"id": cart.id}, 
        status_code=HTTPStatus.CREATED, 
        headers={"location": f"/cart/{cart.id}"}
        )


@router.get("/{cart_id}", response_model=Cart, status_code=HTTPStatus.OK)
async def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart_service = CartService(SqlAlchemyCartRepository(db), SqlAlchemyItemRepository(db))
    cart = cart_service.get_cart(cart_id)
    
    if cart is None:
        return HTTPException(HTTPStatus.NOT_FOUND, "Cart not found!")

    return cart


@router.get("/", status_code=HTTPStatus.OK)
async def get_carts(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeInt, Query()] | None = None,
    max_price: Annotated[NonNegativeInt, Query()] | None = None,
    min_quantity: Annotated[NonNegativeInt, Query()] | None = None,
    max_quantity: Annotated[NonNegativeInt, Query()] | None = None, 
    db: Session = Depends(get_db)
    ):
    if min_price is None:
        min_price = 0
    
    if max_price is None:
        max_price = float("inf") # type: ignore
        
    if min_quantity is None:
        min_quantity = 0
    
    if max_quantity is None:
        max_quantity = float("inf") # type: ignore
        
    cart_service = CartService(SqlAlchemyCartRepository(db), SqlAlchemyItemRepository(db))
    carts = cart_service.get_carts()
    
    carts = list(filter(lambda x: min_price <= x.price <= max_price, carts)) # type: ignore
    
    carts = [cart for cart in carts if min_quantity <= sum([it.quantity for it in cart.items]) <= max_quantity] # type: ignore
    carts = carts[offset: offset + limit]
    return carts

@router.post("/{cart_id}/add/{item_id}")
async def add_item2cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart_service = CartService(SqlAlchemyCartRepository(db), SqlAlchemyItemRepository(db))

    try:
        cart_service.add_item_to_cart(cart_id=cart_id, item_id=item_id, count=1)
    except ValueError as e:
        return HTTPException(HTTPStatus.NOT_FOUND, str(e))
    
    return Response(status_code=HTTPStatus.OK)