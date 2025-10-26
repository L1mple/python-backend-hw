from http import HTTPStatus
from typing import Optional, List, Annotated

from fastapi import APIRouter, HTTPException, Response, Query, Depends
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat

from ...data.deps import get_cart_repo
from ...data.repository import CartRepository
from ..contracts import CartResponse

router = APIRouter(prefix='/cart')

@router.post('/', status_code=HTTPStatus.CREATED)
async def create_cart(repo : CartRepository = Depends(get_cart_repo)):
    cart = repo.create()
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
    min_price : Annotated[Optional[NonNegativeFloat], Query()] = None,
    max_price : Annotated[Optional[NonNegativeFloat], Query()] = None,
    min_quantity : Annotated[Optional[NonNegativeInt], Query()] = None,
    max_quantity : Annotated[Optional[NonNegativeInt], Query()] = None,
    repo : CartRepository = Depends(get_cart_repo)
) -> List[CartResponse]:
    return [
        CartResponse.from_entity(cart)
        for cart in repo.get_carts(
            offset, limit,
            min_price, max_price,
            min_quantity, max_quantity
        )
    ]

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
    cart_id : int,
    repo : CartRepository = Depends(get_cart_repo)
) -> CartResponse:
    entity = repo.find_by_id(cart_id)
    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart with id {cart_id} not found"
        )
    return CartResponse.from_entity(entity)

@router.post(
    '/{cart_id}/add/{item_id}',
    responses={
        HTTPStatus.OK : {
            "description" : "Successfully added item to cart"
        },
        HTTPStatus.NOT_FOUND : {
            "description" : "Failed to add item to cart as item or cart was not found"
        }
    }
)
async def add_item_to_cart(
    cart_id : int,
    item_id : int,
    repo : CartRepository = Depends(get_cart_repo)
):
    try:
        repo.add_to_cart(cart_id, item_id)
    except ValueError as e:
        raise HTTPException(HTTPStatus.NOT_FOUND, str(e)) from e
