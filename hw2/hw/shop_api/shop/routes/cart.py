from http import HTTPStatus
from typing import Optional, List, Annotated

from fastapi import APIRouter, HTTPException, Response, Query
from pydantic import NonNegativeInt, PositiveInt

from ...store import queries
from ..contracts import CartResponse

router = APIRouter(prefix='/cart')

@router.post('/', status_code=HTTPStatus.CREATED)
async def create_cart():
    cart = queries.create_cart()
    return Response(
        content=f'{{"id" : {cart.id}}}',
        media_type="application/json",
        headers={"location" : f"/cart/{cart.id}"},
        status_code=HTTPStatus.CREATED
    )

@router.get('/', status_code=HTTPStatus.OK)
async def get_carts(
    offset : Annotated[NonNegativeInt, Query()] = 0,
    limit : Annotated[PositiveInt, Query()] = 10,
    min_price : Optional[float] = None,
    max_price : Optional[float] = None,
    min_quantity : Optional[int] = None,
    max_quantity : Optional[int] = None
) -> List[CartResponse]:
    if offset < 0:
        raise HTTPException(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "Offset has to be non-negative integer"
        )
    if limit <= 0:
        raise HTTPException(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "Limit has to be positive integer"
        )
    if min_price is not None and min_price < 0 or max_price is not None and max_price < 0:
        raise HTTPException(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "Price has to be non-negative float"
        )
    if min_quantity is not None and min_quantity < 0 or max_quantity is not None and max_quantity < 0:
        raise HTTPException(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "Quantity has to be non-negative integer"
        )
    return [CartResponse.from_entity(e) for e in queries.get_carts(offset, limit, min_price, max_price, min_quantity, max_quantity)]

@router.get(
    '/{cart_id}',
    responses={
        HTTPStatus.OK : {
            "description" : "Successfully returned cart info"
        },
        HTTPStatus.NOT_FOUND : {
            "description" : "Failed to return cart as it was not found"
        }
    }
)
async def get_cart(
    cart_id : int
) -> CartResponse:
    entity = queries.get_cart(cart_id)
    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart with id {cart_id} not found"
        )

    return CartResponse.from_entity(entity)

@router.post('/{cart_id}/add/{item_id}')
async def add_item_to_cart(
    cart_id : int,
    item_id : int
):
    item = queries.get_item(item_id)
    if item is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id {item_id} was not found"
        )

    cart = queries.add_to_cart(cart_id, item)
    if cart is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart with id {cart_id} was not found"
        )
