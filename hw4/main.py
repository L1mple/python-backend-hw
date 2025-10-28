from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db import Base, engine, SessionLocal
import models
from models import Item, Cart, CartItem
from schemas import ItemCreate, ItemPatch, Item as ItemSchema, CartOut, CartItemOut
from typing import List, Optional
from pydantic import conint, PositiveInt, confloat

app = FastAPI()

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- ITEM ENDPOINTS ----------

@app.post('/item', response_model=ItemSchema, status_code=201)
def create_item(item_in: ItemCreate, db: Session = Depends(get_db)):
    item = Item(name=item_in.name, price=item_in.price)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get('/item/{id}', response_model=ItemSchema)
def get_item(id: int, db: Session = Depends(get_db)):
    item = db.get(Item, id)
    if not item or item.deleted:
        raise HTTPException(status_code=404)
    return item


@app.get('/item', response_model=List[ItemSchema])
def list_items(
    offset: conint(ge=0) = 0,
    limit: PositiveInt = 10,
    min_price: Optional[confloat(ge=0.0)] = None,
    max_price: Optional[confloat(ge=0.0)] = None,
    show_deleted: bool = False,
    db: Session = Depends(get_db)
):
    query = db.query(Item)
    if not show_deleted:
        query = query.filter(Item.deleted == False)
    if min_price is not None:
        query = query.filter(Item.price >= min_price)
    if max_price is not None:
        query = query.filter(Item.price <= max_price)

    return query.offset(offset).limit(limit).all()


@app.put('/item/{id}', response_model=ItemSchema)
def replace_item(id: int, item_in: ItemCreate, db: Session = Depends(get_db)):
    item = db.get(Item, id)
    if not item:
        raise HTTPException(status_code=404)
    item.name = item_in.name
    item.price = item_in.price
    db.commit()
    db.refresh(item)
    return item


@app.patch('/item/{id}', response_model=ItemSchema)
def patch_item(id: int, patch: ItemPatch, db: Session = Depends(get_db)):
    item = db.get(Item, id)
    if not item:
        raise HTTPException(status_code=404)
    if item.deleted:
        return JSONResponse(status_code=304, content=item.__dict__)

    data = patch.dict(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


@app.delete('/item/{id}')
def delete_item(id: int, db: Session = Depends(get_db)):
    item = db.get(Item, id)
    if not item:
        return {'ok': True}
    item.deleted = True
    db.commit()
    return {'ok': True}


# ---------- CART ENDPOINTS ----------

@app.post('/cart')
def create_cart(db: Session = Depends(get_db)):
    cart = Cart()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    response = JSONResponse(status_code=201, content={'id': cart.id})
    response.headers['Location'] = f'/cart/{cart.id}'
    return response


@app.post('/cart/{cart_id}/add/{item_id}')
def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = db.get(Cart, cart_id)
    item = db.get(Item, item_id)
    if not cart or not item:
        raise HTTPException(status_code=404)

    cart_item = db.query(CartItem).filter_by(cart_id=cart_id, item_id=item_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(cart_item)
    db.commit()
    return {'ok': True}


def _cart_to_response(cart: Cart, db: Session) -> CartOut:
    items_out = []
    total_price = 0.0

    for cart_item in cart.items:
        item = db.get(Item, cart_item.item_id)
        available = item is not None and not item.deleted
        name = item.name if item else ''
        if available:
            total_price += item.price * cart_item.quantity
        items_out.append(CartItemOut(id=cart_item.item_id, name=name, quantity=cart_item.quantity, available=available))

    return CartOut(id=cart.id, items=items_out, price=total_price)


@app.get('/cart/{id}', response_model=CartOut)
def get_cart(id: int, db: Session = Depends(get_db)):
    cart = db.get(Cart, id)
    if not cart:
        raise HTTPException(status_code=404)
    return _cart_to_response(cart, db)
