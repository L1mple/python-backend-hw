from typing import Annotated

from fastapi import APIRouter, Query, Response, HTTPException, status
from pydantic import NonNegativeInt, PositiveInt

from shop_api.store.queries import create_item_record, list_items, patch_item_record, replace_item_record
from shop_api.store.models import Item
from shop_api.api.item.contracts import ItemPostRequest, ItemPutRequest, ItemPatchRequest


router = APIRouter(prefix="/item")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_item(request: ItemPostRequest, response: Response) -> Item:
    item = create_item_record(request.name, request.price)
    response.headers["Location"] = f"/item/{item.id}"
    return item


@router.get("/")
async def get_items(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[float | None, Query(gt=0)] = None,
    max_price: Annotated[float | None, Query(gt=0)] = None,
    show_deleted: Annotated[bool, Query()] = False,
) -> list[Item]:
    return list_items(
        offset, limit, min_price, max_price, show_deleted
    )


@router.get("/{id}")
async def get_item(id: int) -> Item:
    items = list_items(offset=id, limit=1)
    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return items[0]


@router.put("/{id}")
async def put_item(id: int, request: ItemPutRequest) -> Item:
    items = list_items(offset=id, limit=1)
    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    replace_item_record(items[0].id, request.name, request.price)
    return items[0]


@router.patch("/{id}")
async def patch_item(id: int, request: ItemPatchRequest) -> Item:
    items = list_items(offset=id, limit=1)
    if not items:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED)
    patch_item_record(items[0].id, request.name, request.price)
    return items[0]


@router.delete("/{id}")
async def delete_item(id: int) -> None:
    items = list_items(offset=id, limit=1)
    if not items:
        return
    items[0].deleted = True
