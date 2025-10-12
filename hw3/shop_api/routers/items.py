from fastapi import APIRouter, HTTPException, Query, Response
from shop_api.schemas.item import Item, ItemCreate
from shop_api.storage.memory import _items, _lock, _next_item_id
from typing import Optional, List
from shop_api.metrics import items_in_stock_gauge

router = APIRouter(prefix="/item", tags=["items"])

@router.post("/", response_model=Item, status_code=201)
def create_item(item: ItemCreate):
    global _next_item_id
    with _lock:
        iid = _next_item_id
        _next_item_id += 1
        new_item = Item(id=iid, name=item.name, price=item.price)
        _items[iid] = new_item
        items_in_stock_gauge.inc()
    return new_item

@router.get("/{id}", response_model=Item)
def get_item(id: int):
    item = _items.get(id)
    if not item or item.deleted:
        raise HTTPException(status_code=404, detail="item not found")
    return item

@router.get("/", response_model=List[Item])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False),
):
    items = []
    for it in _items.values():
        if not show_deleted and it.deleted:
            continue
        if min_price is not None and it.price < min_price:
            continue
        if max_price is not None and it.price > max_price:
            continue
        items.append(it)
    return items[offset: offset + limit]

@router.put("/{id}", response_model=Item)
def replace_item(id: int, item: ItemCreate):
    if id not in _items:
        raise HTTPException(status_code=404, detail="item not found")
    existing = _items[id]
    existing.name = item.name
    existing.price = item.price
    _items[id] = existing
    return existing

@router.patch("/{id}", response_model=Item)
def patch_item(id: int, patch: dict):
    if id not in _items:
        raise HTTPException(status_code=404, detail="item not found")
    item = _items[id]
    if item.deleted:
        return Response(status_code=304)
    allowed_keys = {"name", "price"}
    if not set(patch.keys()).issubset(allowed_keys):
        raise HTTPException(status_code=422)
    if "price" in patch:
        price = patch["price"]
        if price is not None and price < 0:
            raise HTTPException(status_code=422)
        item.price = price
    if "name" in patch:
        item.name = patch["name"]
    _items[id] = item
    return item

@router.delete("/{id}")
def delete_item(id: int):
    item = _items.get(id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not item.deleted:
        item.deleted = True
        items_in_stock_gauge.dec()