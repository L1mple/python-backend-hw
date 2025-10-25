from http import HTTPStatus
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import NonNegativeInt, PositiveInt

from shop_api.schemas import Cart

from shop_api import data_storage


router = APIRouter(
    prefix="/cart",
    tags=["cart"],
)

@router.post("/")
async def create_cart():
    cart_id = data_storage.create_cart()
    return JSONResponse(
        {"id": cart_id}, 
        status_code=HTTPStatus.CREATED, 
        headers={"location": f"/cart/{cart_id}"}
        )


@router.get("/{cart_id}", response_model=Cart)
async def get_cart(cart_id: int):
    cart = data_storage.get_cart(cart_id)
    
    if cart is None:
        return HTTPException(HTTPStatus.NOT_FOUND, "Cart not found!")
    
    return JSONResponse(cart, status_code=HTTPStatus.OK)


@router.get("/")
async def get_carts(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeInt, Query()] | None = None,
    max_price: Annotated[NonNegativeInt, Query()] | None = None,
    min_quantity: Annotated[NonNegativeInt, Query()] | None = None,
    max_quantity: Annotated[NonNegativeInt, Query()] | None = None,
    ):
    if min_price is None:
        min_price = 0
    
    if max_price is None:
        max_price = float("inf") # type: ignore
        
    if min_quantity is None:
        min_quantity = 0
    
    if max_quantity is None:
        max_quantity = float("inf") # type: ignore
    
    carts = data_storage.get_carts()
    
    carts = list(filter(lambda x: min_price <= x["price"] <= max_price, carts)) # type: ignore
    
    carts = [cart for cart in carts if min_quantity <= sum([it["quantity"] for it in cart["items"]]) <= max_quantity] # type: ignore
    carts = carts[offset: offset + limit]
    return JSONResponse(carts, status_code=HTTPStatus.OK) 

@router.post("/{cart_id}/add/{item_id}")
async def add_item2cart(cart_id: int, item_id: int):
    if not data_storage.is_cart_exists(cart_id):
        return HTTPException(HTTPStatus.NOT_FOUND, "Cart not found!")
    
    item = data_storage.get_item(item_id=item_id)
    if item is None:
        return HTTPException(HTTPStatus.NOT_FOUND, "Item not found!")
    
    data_storage.add_item2storage(cart_id, item)
    return Response(status_code=HTTPStatus.OK)