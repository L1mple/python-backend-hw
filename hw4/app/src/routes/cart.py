from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db import Base, engine, get_session
from src.repository import CartRepository

Base.metadata.create_all(bind=engine)

class CartItemOut(BaseModel):
    item_id: int
    name: str
    price: float
    quantity: int

class CartOut(BaseModel):
    id: int
    total_price: float
    total_quantity: int
    items: list[CartItemOut]

class CartIdOut(BaseModel):
    id: int

app = APIRouter(prefix='/cart')

@app.post("/", response_model=CartIdOut, status_code=201)
def create_cart(db: Session = Depends(get_session)):
    cart = CartRepository(db).create()
    return CartIdOut(id=cart.id)

@app.get("/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int, db: Session = Depends(get_session)):
    cart = CartRepository(db).get(cart_id)
    if not cart:
        raise HTTPException(404, "Not found")
    return cart

@app.get("/", response_model=list[CartOut])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    min_quantity: Optional[int] = Query(default=None, ge=0),
    max_quantity: Optional[int] = Query(default=None, ge=0),
    db: Session = Depends(get_session),
):
    return CartRepository(db).list(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )

@app.post("/{cart_id}/add/{item_id}", response_model=CartOut)
def add_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_session)):
    cart = CartRepository(db).add_item(cart_id, item_id)
    if not cart:
        raise HTTPException(404, "Cart or item not found (or item deleted)")
    return cart
