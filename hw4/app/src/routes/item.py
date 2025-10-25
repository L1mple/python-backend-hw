from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from db import Base, engine, get_session
from repository import ItemRepository

Base.metadata.create_all(bind=engine)

class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    price: float = Field(ge=0)

class ItemPut(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    price: float = Field(ge=0)

class ItemPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    price: Optional[float] = Field(default=None, ge=0)

class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool

app = APIRouter(prefix="item")

@app.post("/", response_model=ItemOut, status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_session)):
    repo = ItemRepository(db)
    try:
        item = repo.create(payload.name, payload.price)
    except IntegrityError:
        raise HTTPException(409, "Item with this name exists")
    return item

@app.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_session)):
    item = ItemRepository(db).get(item_id)
    if not item:
        raise HTTPException(404, "Not found")
    return item

@app.get("/", response_model=list[ItemOut])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    show_deleted: bool = Query(False),
    db: Session = Depends(get_session),
):
    return ItemRepository(db).list(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted,
    )

@app.put("/{item_id}", response_model=ItemOut)
def put_item(item_id: int, payload: ItemPut, db: Session = Depends(get_session)):
    repo = ItemRepository(db)
    try:
        item = repo.replace(item_id, name=payload.name, price=payload.price)
    except IntegrityError:
        raise HTTPException(409, "Item with this name exists")
    if not item:
        raise HTTPException(404, "Not found")
    return item

@app.patch("/{item_id}", response_model=ItemOut)
def patch_item(item_id: int, payload: ItemPatch, db: Session = Depends(get_session)):
    repo = ItemRepository(db)
    try:
        item = repo.patch(item_id, name=payload.name, price=payload.price)
    except IntegrityError:
        raise HTTPException(409, "Item with this name exists")
    if not item:
        raise HTTPException(404, "Not found")
    return item

@app.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_session)):
    ok = ItemRepository(db).soft_delete(item_id)
    if not ok:
        raise HTTPException(404, "Not found")
    return
