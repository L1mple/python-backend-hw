from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat

from hw2.hw.shop_api.store import item_queries as store

from .item_contracts import (
    PatchItemRequest,
    ItemRequest,
    ItemResponse,
)

item_router = APIRouter(prefix="/item")


@item_router.get("/")
async def get_item_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    show_deleted: Annotated[bool, Query()] = False,
) -> list[ItemResponse]:
    return [
        ItemResponse.from_entity(e)
        for e in store.get_many(
            offset=offset,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
            show_deleted=show_deleted,
        )
    ]


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
    entity = store.get_one(id)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@item_router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_item(info: ItemRequest, response: Response) -> ItemResponse:
    entity = store.add(info.as_item_info())

    response.headers["location"] = f"/item/{entity.id}"

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
    entity = store.patch(id, info.as_patch_item_info())

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@item_router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully updated or upserted item",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify item as one was not found",
        },
    }
)
async def put_item(
    id: int,
    info: ItemRequest,
    upsert: Annotated[bool, Query()] = False,
) -> ItemResponse:
    entity = (
        store.upsert(id, info.as_item_info())
        if upsert
        else store.update(id, info.as_item_info())
    )

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@item_router.delete("/{id}")
async def delete_item(id: int) -> Response:
    store.delete(id)
    return Response("")
