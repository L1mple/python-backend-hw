from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt

from shop_api import store

from .contracts import ItemResponse, ItemRequest, PatchItemRequest

router = APIRouter(prefix="/item")


@router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_item(info: ItemRequest, response: Response) -> ItemResponse:
    entity = store.add_item(info.as_item_info())
    response.headers["location"] = f"/item/{entity.id}"
    return ItemResponse.from_entity(entity)


@router.get(
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
    entity = store.get_item(id)

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@router.get("/")
async def get_item_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    show_deleted: Annotated[bool, Query()] = False,
) -> list[ItemResponse]:
    return [
        ItemResponse.from_entity(e)
        for e in store.get_many_items(offset, limit, min_price, max_price, show_deleted)
    ]


@router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully updated item",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to update item as one was not found",
        },
    },
)
async def put_item(id: int, info: ItemRequest) -> ItemResponse:
    entity = store.replace_item(id, info.as_item_info())

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@router.patch(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully patched item",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify item as one was not found or deleted",
        },
    },
)
async def patch_item(id: int, info: PatchItemRequest) -> ItemResponse:
    entity = store.patch_item(id, info.as_patch_item_info())

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@router.delete(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully deleted item",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to delete item as one was not found",
        },
    },
)
async def delete_item(id: int) -> ItemResponse:
    entity = store.delete_item(id)

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)
