from typing import Optional, List, Annotated
from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Query, Response, Depends
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat

from ...data.deps import get_item_repo
from ...data.repository import ItemRepository
from ..contracts import ItemRequest, ItemResponse, PatchItemRequest

router = APIRouter(prefix='/item')

@router.get('/', response_model=list[ItemResponse])
async def get_items(
    offset : Annotated[NonNegativeInt, Query()] = 0,
    limit : Annotated[PositiveInt, Query()] = 10,
    min_price : Annotated[Optional[NonNegativeFloat], Query()] = None,
    max_price : Annotated[Optional[NonNegativeFloat], Query()] = None,
    show_deleted : bool = False,
    repo : ItemRepository = Depends(get_item_repo)
) -> List[ItemResponse]:
    return [
        ItemResponse.from_entity(item)
        for item in repo.get_items(
            offset, limit,
            min_price, max_price,
            show_deleted
        )
    ]

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
    item_id : int,
    repo : ItemRepository = Depends(get_item_repo)
) -> ItemResponse:
    entity = repo.find_by_id(item_id)
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
    data : ItemRequest,
    repo : ItemRepository = Depends(get_item_repo)
) -> ItemResponse:
    entity = repo.create(data.as_item())
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
    data : ItemRequest,
    repo : ItemRepository = Depends(get_item_repo)
) -> ItemResponse:
    entity = repo.update(item_id, data.as_item())
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
    data : PatchItemRequest,
    repo : ItemRepository = Depends(get_item_repo)
) -> ItemResponse:
    try:
        entity = repo.patch(item_id, data.as_patch_item())
        return ItemResponse.from_entity(entity)
    except ValueError as e:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            str(e)
        ) from e



@router.delete(
    '/{item_id}',
    responses={
        HTTPStatus.OK : {
            "description" : "Successfully patched item"
        },
        HTTPStatus.NOT_FOUND : {
            "description" : "Failed to delete item as it was not found"
        }
    }
)
async def delete_item(
    item_id : int,
    repo : ItemRepository = Depends(get_item_repo)
):
    try:
        repo.delete(item_id)
        return Response(status_code=HTTPStatus.OK)
    except ValueError as e:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            str(e)
        ) from e
