from http import HTTPStatus
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from . import models, schemas
from .db import Base, SessionLocal, engine

app = FastAPI(title="Shop API with DB")

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- ITEM CRUD ----------


@app.post("/item", response_model=schemas.ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    db_item = models.Item(name=item.name, price=item.price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.get("/item/{id}", response_model=schemas.ItemOut)
def get_item(id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == id, models.Item.deleted == False).first()
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found or deleted")
    return item


@app.get("/item", response_model=List[schemas.ItemOut])
def list_items(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
):
    q = db.query(models.Item)
    if not show_deleted:
        q = q.filter(models.Item.deleted == False)
    if min_price is not None:
        q = q.filter(models.Item.price >= min_price)
    if max_price is not None:
        q = q.filter(models.Item.price <= max_price)
    return q.offset(offset).limit(limit).all()


@app.put("/item/{id}", response_model=schemas.ItemOut)
def replace_item(id: int, item: schemas.ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == id).first()
    if not db_item:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Item not found")
    db_item.name = item.name  # type: ignore
    db_item.price = item.price  # type: ignore
    db.commit()
    db.refresh(db_item)
    return db_item


@app.patch("/item/{id}", response_model=schemas.ItemOut)
def patch_item(id: int, patch: schemas.ItemPatch, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == id).first()
    if not db_item:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Item not found")
    if db_item.deleted:  # type: ignore
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
    if patch.name is not None:
        db_item.name = patch.name  # type: ignore
    if patch.price is not None:
        db_item.price = patch.price  # type: ignore
    db.commit()
    db.refresh(db_item)
    return db_item


@app.delete("/item/{id}")
def delete_item(id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == id).first()
    if not db_item:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Item not found")
    db_item.deleted = True  # type: ignore
    db.commit()
    return {"ok": True}


# ---------- CART CRUD ----------


@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart(response: Response, db: Session = Depends(get_db)):
    cart = models.Cart()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    response.headers["Location"] = f"/cart/{cart.id}"
    return {"id": cart.id}


def compute_cart(cart: models.Cart) -> schemas.CartOut:
    items_list = []
    total_price = 0.0
    for ci in cart.items:
        item = ci.item
        available = not item.deleted if item else False
        items_list.append(
            schemas.CartItemOut(
                id=item.id if item else ci.item_id,
                name=item.name if item else "<unknown>",
                quantity=ci.quantity,
                available=available,
            )
        )
        if available:
            total_price += item.price * ci.quantity
    return schemas.CartOut(id=cart.id, items=items_list, price=total_price)  # type: ignore


@app.get("/cart/{id}", response_model=schemas.CartOut)
def get_cart(id: int, db: Session = Depends(get_db)):
    cart = db.query(models.Cart).filter(models.Cart.id == id).first()
    if not cart:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Cart not found")
    return compute_cart(cart)


@app.get("/cart", response_model=List[schemas.CartOut])
def list_carts(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    carts = db.query(models.Cart).offset(offset).limit(limit).all()
    result = []
    for cart in carts:
        c = compute_cart(cart)
        total_qty = sum(ci.quantity for ci in c.items)
        if min_price is not None and c.price < min_price:
            continue
        if max_price is not None and c.price > max_price:
            continue
        if min_quantity is not None and total_qty < min_quantity:
            continue
        if max_quantity is not None and total_qty > max_quantity:
            continue
        result.append(c)
    return result


@app.post("/cart/{cart_id}/add/{item_id}", response_model=schemas.CartOut)
def add_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = db.query(models.Cart).filter(models.Cart.id == cart_id).first()
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not cart:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Cart not found")
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    cart_item = (
        db.query(models.CartItem).filter(models.CartItem.cart_id == cart_id, models.CartItem.item_id == item_id).first()
    )
    if cart_item:
        cart_item.quantity += 1  # type: ignore
    else:
        db.add(models.CartItem(cart_id=cart_id, item_id=item_id, quantity=1))

    db.commit()
    db.refresh(cart)
    return compute_cart(cart)
