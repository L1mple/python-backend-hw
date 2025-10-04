from fastapi import APIRouter, HTTPException, Query, Response
from typing import List, Optional

from ..models import Item, ItemCreate, ItemPut, ItemPatch
from ..storage import (
    next_item_id, save_item, get_item_or_404, get_item_raw, all_items,
)

router = APIRouter(prefix="/item", tags=["item"])


@router.post("", response_model=Item, status_code=201)
def create_item(body: ItemCreate) -> Item:
    iid = next_item_id()
    item = Item(id=iid, name=body.name, price=float(body.price), deleted=False)
    save_item(item)
    return item


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: int) -> Item:
    return get_item_or_404(item_id)


@router.get("", response_model=List[Item])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
) -> List[Item]:
    items = all_items(show_deleted)
    if min_price is not None:
        items = [i for i in items if i.price >= float(min_price)]
    if max_price is not None:
        items = [i for i in items if i.price <= float(max_price)]
    return items[offset: offset + limit]


@router.put("/{item_id}", response_model=Item)
def replace_item(item_id: int, body: ItemPut) -> Item:
    item = get_item_raw(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    new_item = Item(id=item_id, name=body.name, price=float(
        body.price), deleted=body.deleted)
    save_item(new_item)
    return new_item


@router.patch("/{item_id}", response_model=Item)
def patch_item(item_id: int, body: ItemPatch):
    item = get_item_raw(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    if item.deleted:
        return Response(status_code=304)
    if body.name is not None:
        item.name = body.name
    if body.price is not None:
        item.price = float(body.price)
    save_item(item)
    return item


@router.delete("/{item_id}", status_code=200)
def delete_item(item_id: int):
    item = get_item_raw(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    item.deleted = True
    save_item(item)
    return None
