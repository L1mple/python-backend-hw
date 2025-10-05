from __future__ import annotations
from http import HTTPStatus
from fastapi import APIRouter, HTTPException, Path, Query, Response

from shop_api.core.models import Item
from shop_api.core.schemas import ItemCreate, ItemOut, ItemUpdatePatch, ItemUpdatePut
from shop_api.core.store import store

router = APIRouter(tags=["items"])

def _get_item_or_404(item_id: int) -> Item:
    item = store.get_item(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return item

@router.post("/item", status_code=HTTPStatus.CREATED, response_model=ItemOut)
def create_item(body: ItemCreate):
    item_id = store.next_item_id()
    item = Item(id=item_id, name=body.name, price=float(body.price), deleted=False)
    store.items[item_id] = item
    return item

@router.get("/item/{item_id}", response_model=ItemOut)
def get_item(item_id: int = Path(ge=1)):
    return _get_item_or_404(item_id)

@router.get("/item", response_model=list[ItemOut])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    show_deleted: bool = Query(default=False),
):
    items = list(store.items.values())
    if not show_deleted:
        items = [i for i in items if not i.deleted]

    if min_price is not None:
        items = [i for i in items if i.price >= min_price]
    if max_price is not None:
        items = [i for i in items if i.price <= max_price]

    return items[offset : offset + limit]

@router.put("/item/{item_id}", response_model=ItemOut)
def put_item(body: ItemUpdatePut, item_id: int = Path(ge=1)):
    item = _get_item_or_404(item_id)
    item.name = body.name
    item.price = float(body.price)
    store.items[item_id] = item
    return item

@router.patch("/item/{item_id}", response_model=ItemOut, status_code=HTTPStatus.OK)
def patch_item(body: ItemUpdatePatch, item_id: int = Path(ge=1)):
    item = store.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    if item.deleted:
        return Response(status_code=HTTPStatus.NOT_MODIFIED)

    if body.name is not None:
        item.name = body.name
    if body.price is not None:
        item.price = float(body.price)

    store.items[item_id] = item
    return item

@router.delete("/item/{item_id}", status_code=HTTPStatus.OK)
def delete_item(item_id: int = Path(ge=1)):
    item = store.get_item(item_id)
    if item is not None:
        item.deleted = True
        store.items[item_id] = item
    return {"status": "ok"}
