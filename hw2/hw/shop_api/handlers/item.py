from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from shop_api.models.item import ItemCreate, ItemOut, ItemPatch, ItemPut
from shop_api.storage.psql_sqlalchemy import (
    get_item as psql_get_item,
    list_items as psql_list_items,
    create_item as psql_create_item,
    update_item as psql_update_item,
    patch_item as psql_patch_item,
    delete_item as psql_delete_item,
    get_store,
)


router = APIRouter(prefix="/item", tags=["item"])


@router.get("", response_model=list[ItemOut], status_code=HTTPStatus.OK)
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    show_deleted: bool = Query(False),
    deps=Depends(get_store),
):
    rows = psql_list_items(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted,
    )
    return [ItemOut(**r) for r in rows]


@router.get("/{item_id}", response_model=ItemOut, status_code=HTTPStatus.OK)
async def item_by_id(
    item_id: int,
    deps=Depends(get_store),
):
    r = psql_get_item(item_id)
    if not r or r.get("deleted"):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail={"error": "item not found"},
        )
    return ItemOut(**r)


@router.post("", response_model=ItemOut, status_code=HTTPStatus.CREATED)
async def create_item(
    payload: ItemCreate,
    request: Request,
    deps=Depends(get_store),
):
    r = psql_create_item(payload.name, payload.price, payload.description)
    return ItemOut(**r)


@router.put("/{item_id}", response_model=ItemOut, status_code=HTTPStatus.OK)
async def put_item(
    item_id: int,
    payload: ItemPut,
    deps=Depends(get_store),
):
    r = psql_update_item(item_id, payload.name, payload.price, payload.description)
    if not r:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail={"error": "item not found"},
        )
    return ItemOut(**r)


@router.patch("/{item_id}", response_model=ItemOut, status_code=HTTPStatus.OK)
async def patch_item(
    item_id: int,
    payload: ItemPatch,
    deps=Depends(get_store),
):
    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    # check existence and deleted status first
    cur = psql_get_item(item_id)
    if not cur:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail={"error": "item not found"},
        )
    if cur.get("deleted"):
        raise HTTPException(
            status_code=HTTPStatus.NOT_MODIFIED,
            detail={"error": "item is deleted"},
        )
    r = psql_patch_item(item_id, update_data)
    if not r:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail={"error": "item not found"},
        )
    return ItemOut(**r)


@router.delete("/{item_id}", response_model=ItemOut, status_code=HTTPStatus.OK)
async def delete_item(
    item_id: int,
    deps=Depends(get_store),
):
    r = psql_delete_item(item_id)
    if not r:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail={"error": "item not found"},
        )
    return ItemOut(**r)
