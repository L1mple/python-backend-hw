from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import Response
import json
from ..database import get_db
from ..services.service_items import ItemService
from ..factory import ItemCreate, ItemResponse


router = APIRouter(prefix="/item", tags=["items"])

# Dependency для сервиса
def get_item_service(db: Session = Depends(get_db)) -> ItemService:
    return ItemService(db)

@router.post("", status_code=201, response_model=ItemResponse)
async def create_item(
    item: ItemCreate,
    item_service: ItemService = Depends(get_item_service)
):
    return item_service.create_item(item)
    
@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    item_service: ItemService = Depends(get_item_service)
):
    return item_service.get_item(item_id)

@router.get("", response_model=List[ItemResponse])
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
    item_service: ItemService = Depends(get_item_service)
):
    return item_service.list_items(offset, limit, min_price, max_price, show_deleted)

@router.put("/{item_id}", response_model=ItemResponse)
async def replace_item(
    item_id: int, 
    item: ItemCreate,
    item_service: ItemService = Depends(get_item_service)
):
    return item_service.replace_item(item_id, item)

@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int, 
    item: dict,
    item_service: ItemService = Depends(get_item_service)
):
    return item_service.update_item(item_id, item)

@router.delete("/{item_id}", status_code=200)
async def delete_item(
    item_id: int,
    item_service: ItemService = Depends(get_item_service)
):
    return item_service.delete_item(item_id)
