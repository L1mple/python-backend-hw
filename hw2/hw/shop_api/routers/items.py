from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from ..factory import ItemCreate, ItemResponse
from ..services.service_items import ItemService
from ..database import db


item_service = ItemService(db)

router = APIRouter(prefix="/item", tags=["items"])

@router.post("", response_model=ItemResponse)
async def create_item(item: ItemCreate):
    return item_service.create_item(item)

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int):
    return item_service.get_item(item_id)

@router.get("", response_model=List[ItemResponse])
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False
):
    return item_service.list_items(offset, limit, min_price, max_price, show_deleted)

@router.put("/{item_id}", response_model=ItemResponse)
async def replace_item(item_id: int, item: ItemCreate):
    return item_service.replace_item(item_id, item)

@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(item_id: int, item: dict):
    return item_service.update_item(item_id, item)

@router.delete("/{item_id}")
async def delete_item(item_id: int):
    return item_service.delete_item(item_id)
