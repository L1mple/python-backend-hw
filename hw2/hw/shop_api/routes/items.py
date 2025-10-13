from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from ..models import ItemCreate, ItemUpdate, ItemPatch, ItemResponse
from ..storage import storage

router = APIRouter(prefix="/item", tags=["items"])


@router.post("", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate):
    item_id = storage.create_item(item.model_dump())
    return ItemResponse(**storage.get_item_by_id(item_id))


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int):
    item = storage.get_item_by_id(item_id)
    if not item or item.get("deleted", False):
        raise HTTPException(status_code=404, detail="Item not found")
    
    return ItemResponse(**item)


@router.get("", response_model=List[ItemResponse])
def get_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False)
):
    items = storage.get_all_items()
    
    if not show_deleted:
        items = [item for item in items if not item.get("deleted", False)]
    
    if min_price is not None:
        items = [item for item in items if item["price"] >= min_price]
    
    if max_price is not None:
        items = [item for item in items if item["price"] <= max_price]
    
    items = items[offset:offset + limit]
    
    return [ItemResponse(**item) for item in items]


@router.put("/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item_update: ItemUpdate):
    item = storage.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    storage.update_item(item_id, item_update.model_dump())
    return ItemResponse(**storage.get_item_by_id(item_id))


@router.patch("/{item_id}", response_model=ItemResponse)
def patch_item(item_id: int, item_patch: ItemPatch):
    item = storage.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.get("deleted", False):
        raise HTTPException(status_code=304, detail="Item is deleted")
    
    patch_data = item_patch.model_dump(exclude_unset=True)
    for field, value in patch_data.items():
        if value is not None:
            item[field] = value
    
    return ItemResponse(**item)


@router.delete("/{item_id}", status_code=200)
def delete_item(item_id: int):
    item = storage.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    storage.delete_item(item_id)
    return {"message": "Item deleted"}
