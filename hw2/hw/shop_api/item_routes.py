from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt

from . import store
from .contracts import ItemRequest, ItemResponse, PatchItemRequest
from .models import ItemInfo, PatchItemInfo

router = APIRouter(prefix="/item", tags=["item"])


@router.post("/", status_code=HTTPStatus.CREATED)
async def create_item(item_request: ItemRequest, response: Response) -> ItemResponse:
    item_info = ItemInfo(
        name=item_request.name,
        price=item_request.price,
        deleted=False,
    )
    item = store.add_item(item_info)
    
    response.headers["location"] = f"/item/{item.id}"
    
    return ItemResponse.from_entity(item)


@router.get("/{id}")
async def get_item_by_id(id: int) -> ItemResponse:
    item = store.get_item(id)
    
    if not item:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item with id={id} not found",
        )
    
    return ItemResponse.from_entity(item)


@router.get("/")
async def get_items(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    show_deleted: bool = False,
) -> list[ItemResponse]:
    items = store.get_items(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted,
    )
    
    return [ItemResponse.from_entity(item) for item in items]


@router.put("/{id}")
async def update_item(id: int, item_request: ItemRequest) -> ItemResponse:
    item_info = ItemInfo(
        name=item_request.name,
        price=item_request.price,
    )
    
    item = store.update_item(id, item_info)
    
    if not item:
        raise HTTPException(
            status_code=HTTPStatus.NOT_MODIFIED,
            detail=f"Item with id={id} not found",
        )
    
    return ItemResponse.from_entity(item)


@router.patch("/{id}")
async def patch_item(id: int, patch_request: PatchItemRequest) -> ItemResponse:
    patch_info = PatchItemInfo(
        name=patch_request.name,
        price=patch_request.price,
    )
    
    item = store.patch_item(id, patch_info)
    
    if not item:
        raise HTTPException(
            status_code=HTTPStatus.NOT_MODIFIED,
            detail=f"Item with id={id} not found or deleted",
        )
    
    return ItemResponse.from_entity(item)


@router.delete("/{id}")
async def delete_item(id: int) -> Response:
    store.delete_item(id)
    return Response(status_code=HTTPStatus.OK)
