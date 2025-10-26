from __future__ import annotations
from http import HTTPStatus
from fastapi import APIRouter, HTTPException, Path, Query, Depends
from sqlalchemy.orm import Session

from shop_api.core import crud, schemas
from shop_api.core.database import get_db

router = APIRouter(tags=["items"])


@router.post("/item", response_model=schemas.ItemOut, status_code=HTTPStatus.CREATED)
def create_item(body: schemas.ItemCreate, db: Session = Depends(get_db)):
    return crud.create_item(db, body)


@router.get("/item/{item_id}", response_model=schemas.ItemOut)
def get_item(item_id: int = Path(ge=1), db: Session = Depends(get_db)):
    item = crud.get_item(db, item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item


@router.get("/item", response_model=list[schemas.ItemOut])
def list_items(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
):
    items = crud.list_items(db)
    if min_price is not None:
        items = [i for i in items if i.price >= min_price]
    if max_price is not None:
        items = [i for i in items if i.price <= max_price]
    return items[offset: offset + limit]


@router.put("/item/{item_id}", response_model=schemas.ItemOut, status_code=HTTPStatus.OK)
def put_item(item_id: int, body: schemas.ItemUpdatePut, db: Session = Depends(get_db)):
    item = crud.update_item(db, item_id, body)
    if item is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return item


@router.patch("/item/{item_id}", response_model=schemas.ItemOut, status_code=HTTPStatus.OK)
def patch_item(item_id: int, body: schemas.ItemUpdatePatch, db: Session = Depends(get_db)):
    item = crud.update_item(db, item_id, body)
    if item is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return item


@router.delete("/item/{item_id}", status_code=HTTPStatus.OK)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = crud.delete_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return {"status": "ok"}