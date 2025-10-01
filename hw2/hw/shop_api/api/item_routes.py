from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt

from shop_api.store.queries import (
    add_item,
    delete_item,
    get_item,
    get_items,
    patch_item,
    update_item,
)

from .contracts import ItemRequest, ItemResponse, PatchItemRequest

router = APIRouter(prefix="/item")


@router.post(
    "",
    status_code=HTTPStatus.CREATED,
)
async def post_item(item_data: ItemRequest, response: Response) -> ItemResponse:
    entity = add_item(item_data.as_item_info())
    response.headers["location"] = f"/item/{entity.id}"
    return ItemResponse.from_entity(entity)


@router.get(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested item",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Item not found",
        },
    },
)
async def get_item_by_id(id: int) -> ItemResponse:
    entity = get_item(id, include_deleted=False)
    
    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id={id} not found",
        )
    
    return ItemResponse.from_entity(entity)


@router.get("")
async def get_item_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    show_deleted: Annotated[bool, Query()] = False,
) -> list[ItemResponse]:
    entities = get_items(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted,
    )
    
    return [ItemResponse.from_entity(e) for e in entities]


@router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully updated item",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Item not found",
        },
    },
)
async def put_item(id: int, item_data: ItemRequest) -> ItemResponse:
    entity = update_item(id, item_data.as_item_info())
    
    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Item with id={id} not found",
        )
    
    return ItemResponse.from_entity(entity)


@router.patch(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully patched item",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Item not found or deleted",
        },
    },
)
async def patch_item_handler(id: int, patch_data: PatchItemRequest) -> ItemResponse:
    entity = patch_item(id, patch_data.as_patch_item_info())
    
    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Item with id={id} not found or is deleted",
        )
    
    return ItemResponse.from_entity(entity)


@router.delete("/{id}")
async def delete_item_handler(id: int) -> Response:
    delete_item(id)
    return Response(status_code=HTTPStatus.OK)
