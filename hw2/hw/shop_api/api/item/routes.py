from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import ValidationError

from store.database import get_db
from store.queries import ItemQueries
from .contracts import ItemCreate, ItemUpdate, ItemResponse, ItemPatch

router = APIRouter()

@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = ItemQueries.create_item(db, item.name, item.price)
    return {
        "id": db_item.id,
        "name": db_item.name,
        "price": db_item.price,
        "deleted": db_item.deleted
    }

@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    db_item = ItemQueries.get_item(db, item_id)
    if not db_item or db_item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {
        "id": db_item.id,
        "name": db_item.name,
        "price": db_item.price,
        "deleted": db_item.deleted
    }

@router.get("/", response_model=List[ItemResponse])
def get_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False),
    db: Session = Depends(get_db)
):
    items = ItemQueries.get_items(
        db,
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted
    )
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "deleted": item.deleted
        }
        for item in items
    ]

@router.put("/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item: ItemUpdate, db: Session = Depends(get_db)):
    db_item = ItemQueries.update_item(db, item_id, item.name, item.price)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {
        "id": db_item.id,
        "name": db_item.name,
        "price": db_item.price,
        "deleted": db_item.deleted
    }

@router.patch("/{item_id}", response_model=ItemResponse)
def patch_item(item_id: int, item_update: dict, db: Session = Depends(get_db)):
    if "deleted" in item_update:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot update deleted field via PATCH"
        )
    
    try:
        validated_data = ItemPatch(**item_update).dict(exclude_unset=True)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid fields in update data: {e}"
        )
    
    db_item = ItemQueries.patch_item(db, item_id, **validated_data)
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail="Item not found or deleted"
        )
    
    return {
        "id": db_item.id,
        "name": db_item.name,
        "price": db_item.price,
        "deleted": db_item.deleted
    }

@router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    success = ItemQueries.delete_item(db, item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted"}
