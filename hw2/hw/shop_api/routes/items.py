from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from ..models import Item, ItemCreate, ItemUpdate
from ..storage import storage

router = APIRouter(prefix="/item", tags=["items"])

@router.post("/", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate):
    return storage.create_item(item)


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: int):
    item = storage.get_available_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.get("/", response_model=List[Item])
def list_items(
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=1),
        min_price: Optional[float] = Query(None, ge=0),
        max_price: Optional[float] = Query(None, ge=0),
        show_deleted: bool = False
):
    items = storage.list_items(show_deleted=show_deleted)

    if min_price is not None:
        items = [item for item in items if item.price >= min_price]
    if max_price is not None:
        items = [item for item in items if item.price <= max_price]

    return items[offset:offset + limit]


@router.put("/{item_id}", response_model=Item)
def replace_item(item_id: int, item: ItemCreate):
    existing = storage.get_item(item_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    updated_item = storage.replace_item(item_id, item)
    return updated_item


@router.patch("/{item_id}", response_model=Item)
def update_item(item_id: int, item_update: ItemUpdate):
    existing_item = storage.get_available_item(item_id)
    if not existing_item:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail="Item not found or deleted")

    try:
        item = storage.update_item(item_id, item_update)
        return item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{item_id}", response_model=Item)
def delete_item(item_id: int):
    item = storage.delete_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item