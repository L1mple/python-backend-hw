from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt

from shop_api.store.dependencies import get_item_service
from shop_api.store.services import ItemService

from .contracts import ItemResponse, ItemRequest, PatchItemRequest

router = APIRouter(prefix="/item")


@router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_item(
    info: ItemRequest,
    response: Response,
    service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    try:
        entity = service.create_item(info.name, info.price)
        response.headers["location"] = f"/item/{entity.id}"
        return ItemResponse.from_entity(entity)
    except ValueError as e:
        raise HTTPException(HTTPStatus.BAD_REQUEST, str(e))


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
async def get_item_by_id(
    id: int,
    service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    try:
        entity = service.get_item(id)
        return ItemResponse.from_entity(entity)
    except ValueError as e:
        raise HTTPException(HTTPStatus.NOT_FOUND, str(e))


@router.get("/")
async def get_item_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    show_deleted: Annotated[bool, Query()] = False,
    service: ItemService = Depends(get_item_service),
) -> list[ItemResponse]:
    # For list operations, we can call repository directly through service
    # Or add a method to service if needed
    entities = service.item_repo.find_many(
        offset, limit, min_price, max_price, show_deleted
    )
    return [ItemResponse.from_entity(e) for e in entities]


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
async def put_item(
    id: int,
    info: ItemRequest,
    service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    try:
        entity = service.update_item(id, info.name, info.price)
        return ItemResponse.from_entity(entity)
    except ValueError as e:
        raise HTTPException(HTTPStatus.NOT_FOUND, str(e))


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
async def patch_item(
    id: int,
    info: PatchItemRequest,
    service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    # Patch is a repository-level operation (no special business logic needed)
    entity = service.item_repo.patch(id, info.as_patch_item_info())

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
async def delete_item(
    id: int,
    service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    # Delete is a repository-level operation (soft delete)
    entity = service.item_repo.delete(id)

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)
