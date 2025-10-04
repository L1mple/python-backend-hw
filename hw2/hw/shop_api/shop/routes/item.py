from typing import Optional, List, Annotated
from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt

from ...store import queries
from ..contracts import ItemRequest, ItemResponse, PatchItemRequest

router = APIRouter(prefix='/item')

@router.get('/')
async def get_items(
    offset : Annotated[NonNegativeInt, Query()] = 0,
    limit : Annotated[PositiveInt, Query()] = 10,
    min_price : Optional[float] = None,
    max_price : Optional[float] = None,
    show_deleted : bool = False
) -> List[ItemResponse]:
    if offset < 0:
        raise HTTPException(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "Offset has to be non-negative integer"
        )
    if limit <= 0:
        raise HTTPException(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "Limit has to be positive integer"
        )
    if min_price is not None and min_price < 0 or max_price is not None and max_price < 0:
        raise HTTPException(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "Price has to be non-negative float"
        )
    return [ItemResponse.from_entity(e) for e in queries.get_items(offset, limit, min_price, max_price, show_deleted)]

@router.get(
    '/{item_id}',
    responses={
        HTTPStatus.OK : {
            "description" : "Successfully returned requested item"
        },
        HTTPStatus.NOT_FOUND : {
            "description" : "Failed to return requested item as it was not found"
        }
    }
)
async def get_item(
    item_id : int
) -> ItemResponse:
    entity = queries.get_item(item_id)
    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id {item_id} was not found"
        )

    return ItemResponse.from_entity(entity)

@router.post(
    '/',
    status_code=HTTPStatus.CREATED
)
def post_item(
    data : ItemRequest
) -> ItemResponse:
    entity = queries.add_item(data.as_item_info())
    return ItemResponse.from_entity(entity)

@router.put(
    '/{item_id}',
    responses={
        HTTPStatus.OK : {
            "description" : "Successfully replaced item"
        },
        HTTPStatus.NOT_MODIFIED : {
            "description" : "Failed to replace item as it was not found"
        }
    }
)
async def put_item(
    item_id : int,
    data : ItemRequest
) -> ItemResponse:
    entity = queries.update_item(item_id, data.as_item_info())
    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Item with id {item_id} was not found"
        )

    return ItemResponse.from_entity(entity)

@router.patch(
    '/{item_id}',
    responses={
        HTTPStatus.OK : {
            "description" : "Successfully patched item"
        },
        HTTPStatus.NOT_MODIFIED : {
            "description" : "Failed to patch item as it was not found"
        }
    }
)
async def patch_item(
    item_id : int,
    data : PatchItemRequest
) -> ItemResponse:
    entity = queries.patch_item(item_id, data.as_patch_item_info())
    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Item with id {item_id} was not found"
        )

    return ItemResponse.from_entity(entity)

@router.delete('/{item_id}')
async def delete_item(
    item_id : int
):
    queries.delete_item(item_id)
    return Response("")
