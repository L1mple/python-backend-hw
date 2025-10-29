from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt

from . import store
from .contracts import CartIdResponse, CartResponse

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/", status_code=HTTPStatus.CREATED)
async def create_cart(response: Response) -> CartIdResponse:
    cart = store.create_cart()
    
    response.headers["location"] = f"/cart/{cart.id}"
    
    return CartIdResponse(id=cart.id)


@router.get("/{id}")
async def get_cart_by_id(id: int) -> CartResponse:
    cart = store.get_cart(id)
    
    if not cart:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Cart with id={id} not found",
        )
    
    return CartResponse.from_entity(cart)


@router.get("/")
async def get_carts(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    min_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    max_quantity: Annotated[NonNegativeInt | None, Query()] = None,
) -> list[CartResponse]:
    carts = store.get_carts(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )
    
    return [CartResponse.from_entity(cart) for cart in carts]


@router.post("/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int) -> CartResponse:
    cart = store.add_item_to_cart(cart_id, item_id)
    
    if not cart:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Cart with id={cart_id} or item with id={item_id} not found",
        )
    
    return CartResponse.from_entity(cart)
