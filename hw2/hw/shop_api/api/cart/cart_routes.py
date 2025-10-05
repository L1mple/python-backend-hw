from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat

from hw2.hw.shop_api.store import cart_queries as store

from .cart_contracts import (
    PatchCartRequest,
    CartRequest,
    CartResponse,
)

cart_router = APIRouter(prefix="/cart")


@cart_router.get("/")
async def get_cart_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    min_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    max_quantity: Annotated[NonNegativeInt | None, Query()] = None,
) -> list[CartResponse]:
    return [
        CartResponse.from_entity(e)
        for e in store.get_many(
            offset=offset,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
        )
    ]


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
    entity = store.get_one(id)

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
async def post_cart(response: Response) -> dict[str, int]:
    entity = store.add_empty()

    response.headers["location"] = f"/cart/{entity.id}"
    return {"id": entity.id}


@cart_router.patch(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully patched cart",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify cart as one was not found",
        },
    },
)
async def patch_cart(id: int, info: PatchCartRequest) -> CartResponse:
    entity = store.patch(id, info.as_patch_cart_info())

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /cart/{id} was not found",
        )

    return CartResponse.from_entity(entity)


@cart_router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully updated or upserted cart",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify cart as one was not found",
        },
    }
)
async def put_cart(
    id: int,
    info: CartRequest,
    upsert: Annotated[bool, Query()] = False,
) -> CartResponse:
    entity = (
        store.upsert(id, info.as_cart_info())
        if upsert
        else store.update(id, info.as_cart_info())
    )

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /cart/{id} was not found",
        )

    return CartResponse.from_entity(entity)


@cart_router.post("/{cart_id}/add/{item_id}")
async def add_item(cart_id: int, item_id: int) -> Response:
    entity = store.add_item(cart_id, item_id)
    if entity is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"/cart/{cart_id} not found")
    return Response("")
