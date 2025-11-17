from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response

from ..schemas import Item, ItemCreate, ItemPatch, ItemPut
from ..storage import (
    create_item as db_create_item,
    get_item as db_get_item,
    list_items as db_list_items,
    patch_item as db_patch_item,
    replace_item as db_replace_item,
    soft_delete_item as db_soft_delete_item,
)


router = APIRouter(prefix="/item")


@router.post("", status_code=201)
def create_item(body: ItemCreate, response: Response) -> Item:
    item = db_create_item(body.name, body.price)
    response.headers["Location"] = f"/item/{item.id}"
    return item


@router.get("/{item_id}")
def get_item(item_id: int) -> Item:
    item = db_get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("")
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    show_deleted: bool = False,
) -> List[Item]:
    return db_list_items(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted,
    )


@router.put("/{item_id}")
def put_item(item_id: int, body: ItemPut) -> Item:
    item = db_replace_item(item_id, body.name, body.price)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.patch("/{item_id}")
def patch_item(item_id: int, body: ItemPatch) -> Item:
    status, item = db_patch_item(item_id, name=body.name, price=body.price)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Item not found")
    if status == "deleted":
        raise HTTPException(status_code=304, detail="Item is deleted")
    assert item is not None
    return item


@router.delete("/{item_id}")
def delete_item(item_id: int) -> dict:
    db_soft_delete_item(item_id)
    return {"status": "ok"}


