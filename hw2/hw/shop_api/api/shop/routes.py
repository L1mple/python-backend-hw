from http import HTTPStatus
from typing import Annotated
import asyncio

from fastapi import APIRouter, HTTPException, Query, Response, Depends
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from ... import data
from ...database import get_db

from .contracts import (
    CartResponse,
    ItemResponse,
    ItemRequest,
    PatchItemRequest,
)

cart_router = APIRouter(prefix="/cart")
item_router = APIRouter(prefix="/item")


@item_router.get("/slow")
async def slow_endpoint(delay: Annotated[float, Query(ge=0, le=30)] = 5.0):
    """Slow endpoint for testing Active Connections metric (delays response)."""
    await asyncio.sleep(delay)
    return {"message": f"Delayed response after {delay}s"}


@cart_router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_cart(
    response: Response,
    session: AsyncSession = Depends(get_db)
) -> CartResponse:
    """Creates new cart"""

    entity = await data.cart_queries.add(session, data.CartInfo(items=[], price=0.0))
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
async def get_cart_by_id(
    id: int,
    session: AsyncSession = Depends(get_db)
) -> CartResponse:
    """Returns cart by id"""

    entity = await data.cart_queries.get_one(session, id)

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
    session: AsyncSession = Depends(get_db),
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

    entities = await data.cart_queries.get_many(
        session, offset, limit, min_price, max_price, min_quantity, max_quantity
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
    cart_id: int,
    item_id: int,
    response: Response,
    session: AsyncSession = Depends(get_db)
) -> CartResponse:
    """Adds item to cart"""

    entity = await data.cart_queries.add_item_to_cart(session, cart_id, item_id, 1)

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
async def post_item(
    item: ItemRequest,
    response: Response,
    session: AsyncSession = Depends(get_db)
) -> ItemResponse:
    entity = await data.item_queries.add(session, item.as_item_info())
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
async def get_item_by_id(
    id: int,
    session: AsyncSession = Depends(get_db)
) -> ItemResponse:
    """Returns item by id"""

    entity = await data.item_queries.get_one(session, id)

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
    session: AsyncSession = Depends(get_db),
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

    entities = await data.item_queries.get_many(
        session, offset, limit, min_price, max_price, show_deleted
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
    session: AsyncSession = Depends(get_db),
    upsert: Annotated[bool, Query()] = False,
) -> ItemResponse:
    """Updates or upserts item by id"""

    existing = await data.item_queries.get_one(session, id)
    if not upsert and existing is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    entity = (
        await data.item_queries.upsert(session, id, info.as_item_info())
        if upsert
        else await data.item_queries.update(session, id, info.as_item_info())
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
async def patch_item(
    id: int,
    info: PatchItemRequest,
    session: AsyncSession = Depends(get_db)
) -> ItemResponse:
    """Patches item by id"""

    existing = await data.item_queries.get_one(session, id)
    if existing and existing.info.deleted:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    entity = await data.item_queries.patch(session, id, info.as_patch_item_info())

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
async def delete_item(
    id: int,
    session: AsyncSession = Depends(get_db)
) -> ItemResponse:
    """Deletes item by id"""

    entity = await data.item_queries.delete(session, id)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item {id} not found",
        )

    return ItemResponse.from_entity(entity)
