from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response

from ..schemas import Item, ItemCreate, ItemPatch, ItemPut
from ..storage import items_by_id, next_item_id


router = APIRouter(prefix="/item")


@router.post("", status_code=201)
def create_item(body: ItemCreate, response: Response) -> Item:
    global next_item_id
    item = Item(id=next_item_id, name=body.name, price=body.price, deleted=False)
    items_by_id[item.id] = item
    response.headers["Location"] = f"/item/{item.id}"
    next_item_id += 1
    return item


@router.get("/{item_id}")
def get_item(item_id: int) -> Item:
    item = items_by_id.get(item_id)
    if item is None or item.deleted:
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
    data = list(items_by_id.values())
    if not show_deleted:
        data = [i for i in data if not i.deleted]
    if min_price is not None:
        data = [i for i in data if i.price >= min_price]
    if max_price is not None:
        data = [i for i in data if i.price <= max_price]
    return data[offset : offset + limit]


@router.put("/{item_id}")
def put_item(item_id: int, body: ItemPut) -> Item:
    item = items_by_id.get(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    item.name = body.name
    item.price = body.price
    return item


@router.patch("/{item_id}")
def patch_item(item_id: int, body: ItemPatch) -> Item:
    item = items_by_id.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.deleted:
        raise HTTPException(status_code=304, detail="Item is deleted")
    if body.name is not None:
        item.name = body.name
    if body.price is not None:
        item.price = body.price
    return item


@router.delete("/{item_id}")
def delete_item(item_id: int) -> dict:
    item = items_by_id.get(item_id)
    if item is not None:
        item.deleted = True
    return {"status": "ok"}


