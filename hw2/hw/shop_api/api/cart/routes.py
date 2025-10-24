from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, Request
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat

from hw2.hw.shop_api import store

from .contracts import CartResponse

router = APIRouter(prefix="/cart")


@router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_cart(_: Request, response: Response) -> CartResponse:
    entity = store.add_cart()

    # as REST states one should provide uri to newly created resource in location header
    response.headers["location"] = f"/cart/{entity.id}"

    return CartResponse.from_entity(entity)


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
    entity = store.get_one_cart(id)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /cart/{id} was not found",
        )

    return CartResponse.from_entity(entity)


@router.get("/")
async def get_cart_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat, Query()] = 0,
    max_price: Annotated[NonNegativeFloat, Query()] = 1e10,
    min_quantity: Annotated[NonNegativeInt, Query()] = 0,
    max_quantity: Annotated[NonNegativeInt, Query()] = 1e10,
) -> list[CartResponse]:
    return [CartResponse.from_entity(e) for e in store.get_many_carts(offset, limit, min_price, max_price, min_quantity, max_quantity)]


@router.post(
    "/{cart_id}/add/{item_id}",
    status_code=HTTPStatus.CREATED,
)
async def post_item_to_cart(cart_id: int, item_id: int, response: Response) -> CartResponse:
    entity = store.add_item_to_cart(cart_id, item_id)

    # as REST states one should provide uri to newly created resource in location header
    response.headers["location"] = f"/cart/{entity.id}"

    return CartResponse.from_entity(entity)
