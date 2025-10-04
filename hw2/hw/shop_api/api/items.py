from __future__ import annotations

from http import HTTPStatus
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/item", tags=["items"])


@router.post("", response_model=schemas.ItemResponse, status_code=HTTPStatus.CREATED)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    """Создание нового товара"""
    db_item = models.Item(name=item.name, price=item.price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/{item_id}", response_model=schemas.ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """Получение товара по ID"""
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    if item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item


@router.get("", response_model=list[schemas.ItemResponse])
def get_items(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 10,
    min_price: Annotated[Optional[float], Query(ge=0)] = None,
    max_price: Annotated[Optional[float], Query(ge=0)] = None,
    show_deleted: bool = False,
    db: Session = Depends(get_db),
):
    """Получение списка товаров с фильтрацией"""
    query = db.query(models.Item)

    if not show_deleted:
        query = query.filter(models.Item.deleted == False)

    if min_price is not None:
        query = query.filter(models.Item.price >= min_price)

    if max_price is not None:
        query = query.filter(models.Item.price <= max_price)

    items = query.offset(offset).limit(limit).all()
    return items


@router.put("/{item_id}", response_model=schemas.ItemResponse)
def update_item(item_id: int, item: schemas.ItemUpdate, db: Session = Depends(get_db)):
    """Полная замена товара по ID"""
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    db_item.name = item.name
    db_item.price = item.price
    db.commit()
    db.refresh(db_item)
    return db_item


@router.patch("/{item_id}", response_model=schemas.ItemResponse)
def patch_item(item_id: int, item: schemas.ItemPatch, db: Session = Depends(get_db)):
    """Частичное обновление товара по ID"""
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    if db_item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED, detail="Item is deleted")

    if item.name is not None:
        db_item.name = item.name
    if item.price is not None:
        db_item.price = item.price

    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Удаление товара по ID (пометка как удаленный)"""
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    db_item.deleted = True
    db.commit()
    return {"message": "Item deleted"}

