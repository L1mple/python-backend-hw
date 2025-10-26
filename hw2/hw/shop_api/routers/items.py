from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ..schemas import Item, ItemCreate, ItemUpdate
from ..storages import ItemStorage
from http import HTTPStatus

router = APIRouter(prefix="/item", tags=["items"])



@router.post("/", response_model=Item, status_code=HTTPStatus.CREATED)
def create_item(item: ItemCreate):
    return ItemStorage.create(item)


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: int):
    item = ItemStorage.get(item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item


@router.get("/", response_model=List[Item])
def get_items(
        offset: int = Query(0, ge=0),
        limit: int = Query(10, gt=0),
        min_price: Optional[float] = Query(None, ge=0),
        max_price: Optional[float] = Query(None, ge=0),
        show_deleted: bool = Query(False)
):
    items = ItemStorage.get_all()

    # Apply filters
    filtered_items = []
    for item in items:
        if not show_deleted and item.deleted:
            continue
        if min_price is not None and item.price < min_price:
            continue
        if max_price is not None and item.price > max_price:
            continue
        filtered_items.append(item)

    # Apply pagination
    return filtered_items[offset:offset + limit]


@router.put("/{item_id}", response_model=Item)
def replace_item(item_id: int, item: ItemCreate):
    if not ItemStorage.exists(item_id):
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    existing_item = ItemStorage.get(item_id)
    if existing_item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    updated_item = Item(id=item_id, **item.dict(), deleted=existing_item.deleted)
    ItemStorage.update(updated_item)
    return updated_item


@router.patch("/{item_id}", response_model=Item)
def update_item(item_id: int, item_update: ItemUpdate):
    existing_item = ItemStorage.get(item_id)
    if not existing_item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    if existing_item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED)

    update_data = item_update.dict(exclude_unset=True)
    updated_item = existing_item.copy(update=update_data)
    ItemStorage.update(updated_item)
    return updated_item


@router.delete("/{item_id}", response_model=Item)
def delete_item(item_id: int):
    item = ItemStorage.get(item_id)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    ItemStorage.delete(item_id)
    return ItemStorage.get(item_id)