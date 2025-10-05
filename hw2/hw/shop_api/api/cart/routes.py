from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt

from shop_api import store
from shop_api.store.models import CartInfo

from .contracts import CartResponse, CartIdResponse

router = APIRouter(prefix="/cart")


@router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_cart(response: Response) -> CartIdResponse:
    """Create a new empty cart (RPC-style endpoint)"""
    entity = store.add_cart(CartInfo(items=[]))
    response.headers["location"] = f"/cart/{entity.id}"
    return CartIdResponse.from_entity(entity)


@router.get(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested cart",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to return requested cart as one was not found",
        },
    },
)
async def get_cart_by_id(id: int) -> CartResponse:
    """Get cart by ID"""
    entity = store.get_cart(id)

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /cart/{id} was not found",
        )

    return CartResponse.from_entity(entity)


@router.get("/")
async def get_cart_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    min_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    max_quantity: Annotated[NonNegativeInt | None, Query()] = None,
) -> list[CartResponse]:
    """Get list of carts with optional filtering"""
    return [
        CartResponse.from_entity(e)
        for e in store.get_many_carts(
            offset, limit, min_price, max_price, min_quantity, max_quantity
        )
    ]


@router.post(
    "/{cart_id}/add/{item_id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully added item to cart",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Cart or item not found",
        },
    },
)
async def add_item_to_cart(cart_id: int, item_id: int) -> CartResponse:
    """Add item to cart (or increment quantity if already exists)"""
    result = store.add_item_to_cart(cart_id, item_id)

    if result is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart {cart_id} or item {item_id} not found",
        )

    # Return updated cart
    entity = store.get_cart(cart_id)
    return CartResponse.from_entity(entity)
