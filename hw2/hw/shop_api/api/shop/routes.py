from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import Field

from ... import data

from .contracts import (
    CartResponse,
    ItemResponse,
    ItemRequest,
    PatchItemRequest,
)

cart_router = APIRouter(prefix="/cart")
item_router = APIRouter(prefix="/item")


@cart_router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_cart(response: Response) -> CartResponse:
    """Creates new cart"""

    entity = data.cart_queries.add(data.CartInfo(items=[], price=0.0))
    response.headers["location"] = f"/cart/{entity.id}"
    return CartResponse.from_entity(entity)


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
    """Returns cart by id"""

    entity = data.cart_queries.get_one(id)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /cart/{id} was not found",
        )

    return CartResponse.from_entity(entity)


@cart_router.get(
    "/",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested carts list by query params",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to return requested carts list by query params",
        },
    },
)
async def get_carts_list(
    offset: Annotated[int | None, Field(ge=0), Query(description="Page number")] = 0,
    limit: Annotated[int | None, Field(ge=1), Query(description="Page size")] = 10,
    min_price: Annotated[
        float | None, Field(ge=0), Query(description="Minimum price")
    ] = None,
    max_price: Annotated[
        float | None, Field(ge=0), Query(description="Maximum price")
    ] = None,
    min_quantity: Annotated[
        int | None, Field(ge=0), Query(description="Minimum quantity")
    ] = None,
    max_quantity: Annotated[
        int | None, Field(ge=0), Query(description="Maximum quantity")
    ] = None,
) -> list[CartResponse]:
    """Returns carts list by query params"""

    entities = data.cart_queries.get_many(
        offset, limit, min_price, max_price, min_quantity, max_quantity
    )

    if not entities:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /cart/ was not found",
        )

    return [CartResponse.from_entity(entity) for entity in entities]


@cart_router.post(
    "/{cart_id}/add/{item_id}",
    status_code=HTTPStatus.CREATED,
)
async def post_item_to_cart(
    cart_id: int, item_id: int, response: Response
) -> CartResponse:
    """Adds item to cart"""

    entity = data.cart_queries.add_item_to_cart(cart_id, item_id, 1)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart {cart_id} or item {item_id} not found",
        )

    response.headers["location"] = f"/cart/{cart_id}"

    return CartResponse.from_entity(entity)


@item_router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_item(item: ItemRequest, response: Response) -> ItemResponse:
    entity = data.item_queries.add(item.as_item_info())
    response.headers["location"] = f"/item/{entity.id}"
    return ItemResponse.from_entity(entity)


@item_router.get(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested item",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to return requested item as one was not found",
        },
    },
)
async def get_item_by_id(id: int) -> ItemResponse:
    """Returns item by id"""

    entity = data.item_queries.get_one(id)

    if not entity or entity.info.deleted:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@item_router.get(
    "/",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested items list by query params",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to return requested items list by query params",
        },
    },
)
async def get_items_list(
    offset: Annotated[int | None, Field(ge=0), Query(description="Page number")] = 0,
    limit: Annotated[int | None, Field(ge=1), Query(description="Page size")] = 10,
    min_price: Annotated[
        float | None, Field(ge=0), Query(description="Minimum price")
    ] = None,
    max_price: Annotated[
        float | None, Field(ge=0), Query(description="Maximum price")
    ] = None,
    show_deleted: Annotated[
        bool | None, Query(description="Show deleted items")
    ] = False,
) -> list[ItemResponse]:
    """Returns items list by query params"""

    entities = data.item_queries.get_many(
        offset, limit, min_price, max_price, show_deleted
    )

    if not entities:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /item/ was not found",
        )

    return [ItemResponse.from_entity(entity) for entity in entities]


@item_router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully updated or upserted item",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify item as one was not found",
        },
    },
)
async def put_item(
    id: int,
    info: ItemRequest,
    upsert: Annotated[bool, Query()] = False,
) -> ItemResponse:
    """Updates or upserts item by id"""

    existing = data.item_queries.get_one(id)
    if not upsert and existing is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    entity = (
        data.item_queries.upsert(id, info.as_item_info())
        if upsert
        else data.item_queries.update(id, info.as_item_info())
    )

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@item_router.patch(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully patched item",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify item as one was not found",
        },
    },
)
async def patch_item(id: int, info: PatchItemRequest) -> ItemResponse:
    """Patches item by id"""

    existing = data.item_queries.get_one(id)
    if existing.info.deleted:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    entity = data.item_queries.patch(id, info.as_patch_item_info())

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@item_router.delete(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Item successfully deleted (marked as deleted)",
        },
    },
)
async def delete_item(id: int) -> ItemResponse:
    """Deletes item by id"""

    entity = data.item_queries.delete(id)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item {id} not found",
        )

    return ItemResponse.from_entity(entity)
