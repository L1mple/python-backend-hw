from http import HTTPStatus
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat

from shop_api import store

from .contracts import (
    CartResponse
)

cart_router = APIRouter(prefix="/cart")


@cart_router.get("/")
async def get_cart_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    min_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    max_quantity: Annotated[NonNegativeInt | None, Query()] = None
) -> list[CartResponse]:
    return [CartResponse.from_entity(e) for e in store.get_carts(offset, limit, min_price, max_price, min_quantity, max_quantity)]


@cart_router.get(
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
    entity = store.get_cart(id)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /cart/{id} was not found",
        )

    return CartResponse.from_entity(entity)


@cart_router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_cart(response: Response) -> CartResponse:
    entity = store.add_cart()

    # as REST states one should provide uri to newly created resource in location header
    response.headers["location"] = f"/cart/{entity.id}"

    return CartResponse.from_entity(entity)


@cart_router.post(
    "/cart/{cart_id}/add/{item_id}",
    status_code=HTTPStatus.CREATED,
)
async def post_cart_item(cart_id: int, item_id: int) -> CartResponse:
    entity_cart = store.get_cart(cart_id)

    if not entity_cart:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /cart/{id} was not found",
        )
    

    entity_item = store.get_item(id)

    if not entity_item:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /item/{id} was not found",
        )
    
    ret_entity_cart = store.add_item_to_cart(cart_id=cart_id, item_id=item_id)

    return CartResponse.from_entity(ret_entity_cart)
