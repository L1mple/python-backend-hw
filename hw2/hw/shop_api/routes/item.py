from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from ..db import items_db
from ..models.item import Item, ItemCreate, ItemPut, ItemPatch

router = APIRouter(prefix='/item')


@router.get('/{id}')
def get_item(id: int):
    if id not in items_db:
        raise HTTPException(status_code=404, detail="Not found")
    if items_db[id].deleted:
        raise HTTPException(status_code=404, detail="Not found")
    return items_db[id]


@router.get('/')
def get_items(
        limit: Optional[int] = Query(default=10, ge=1),
        offset: Optional[int] = Query(default=0, ge=0),
        min_price: Optional[float] = Query(default=None, ge=0),
        max_price: Optional[float] = Query(default=None, ge=0),
        show_deleted: Optional[bool] = False
):
    items = items_db.values()
    if not show_deleted:
        items = filter(lambda x: not x.deleted, items)
    if min_price:
        items = filter(lambda x: x.price >= min_price, items)
    if max_price:
        items = filter(lambda x: x.price <= max_price, items)
    return list(items)[offset:offset + limit]


@router.post('/', status_code=201)
def create_item(item: ItemCreate):
    item = Item(id=len(items_db), name=item.name, price=item.price, deleted=False)
    items_db[item.id] = item
    return item


@router.put('/{id}')
def put_item(id: int, item: ItemPut):
    if id not in items_db:
        raise HTTPException(status_code=404, detail="Not found")
    items_db[id] = Item(id=id, name=item.name, price=item.price, deleted=item.deleted or items_db[id].deleted)
    return items_db[id]


@router.patch('/{id}')
def patch_item(id: int, item: ItemPatch):
    if id not in items_db:
        raise HTTPException(status_code=404, detail="Not found")
    if items_db[id].deleted:
        raise HTTPException(status_code=304, detail="Was deleted")
    if item.price:
        items_db[id].price = item.price
    if item.name:
        items_db[id].name = item.name
    return items_db[id]


@router.delete('/{id}')
def delete_item(id: int):
    if id not in items_db:
        raise HTTPException(status_code=404, detail="Not found")
    items_db[id].deleted = True
    return
