from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from prometheus_fastapi_instrumentator import Instrumentator
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop:shop@localhost:5432/shop")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)


class CartDB(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)


class CartItemDB(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, nullable=False)
    item_id = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1)


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)


class Item(ItemCreate):
    id: int
    deleted: bool = False


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class Cart(BaseModel):
    id: int
    items: List[CartItem] = []
    price: float = 0.0


app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/item", response_model=Item, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = ItemDB(name=item.name, price=item.price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return Item(id=db_item.id, **item.dict(), deleted=False)


@app.get("/item/{id}", response_model=Item)
def get_item(id: int, db: Session = Depends(get_db)):
    item = db.get(ItemDB, id)
    if not item or item.deleted:
        raise HTTPException(404, "Item not found")
    return Item.from_orm(item)


@app.get("/item")
def list_items(
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=1),
        min_price: Optional[float] = Query(None, ge=0),
        max_price: Optional[float] = Query(None, ge=0),
        show_deleted: bool = False,
        db: Session = Depends(get_db)
):
    query = db.query(ItemDB)
    if not show_deleted:
        query = query.filter(ItemDB.deleted == False)
    if min_price is not None:
        query = query.filter(ItemDB.price >= min_price)
    if max_price is not None:
        query = query.filter(ItemDB.price <= max_price)
    items = query.offset(offset).limit(limit).all()
    return [Item.from_orm(i) for i in items]


@app.put("/item/{id}", response_model=Item)
def update_item(id: int, item: ItemCreate, db: Session = Depends(get_db)):
    db_item = db.get(ItemDB, id)
    if not db_item:
        raise HTTPException(404, "Item not found")
    db_item.name = item.name
    db_item.price = item.price
    db.commit()
    db.refresh(db_item)
    return Item.from_orm(db_item)


@app.patch("/item/{id}", response_model=Item)
def partial_update_item(id: int, item: dict, db: Session = Depends(get_db)):
    db_item = db.get(ItemDB, id)
    if not db_item:
        raise HTTPException(404, "Item not found")
    if db_item.deleted:
        raise HTTPException(304, "Item is deleted")
    for key, value in item.items():
        if key in ["name", "price"]:
            setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return Item.from_orm(db_item)


@app.delete("/item/{id}")
def delete_item(id: int, db: Session = Depends(get_db)):
    db_item = db.get(ItemDB, id)
    if not db_item:
        raise HTTPException(404, "Item not found")
    db_item.deleted = True
    db.commit()
    return {"status": "success"}


@app.post("/cart", status_code=201)
def create_cart(db: Session = Depends(get_db)):
    cart = CartDB()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return JSONResponse(
        content={"id": cart.id},
        headers={"Location": f"/cart/{cart.id}"}
    )


@app.get("/cart/{id}", response_model=Cart)
def get_cart(id: int, db: Session = Depends(get_db)):
    cart = db.get(CartDB, id)
    if not cart:
        raise HTTPException(404, "Cart not found")

    items = db.query(CartItemDB).filter(CartItemDB.cart_id == id).all()
    total = 0.0
    cart_items = []
    for ci in items:
        item = db.get(ItemDB, ci.item_id)
        if item and not item.deleted:
            cart_items.append(CartItem(
                id=item.id, name=item.name, quantity=ci.quantity, available=True
            ))
            total += item.price * ci.quantity
        else:
            cart_items.append(CartItem(
                id=ci.item_id, name="Unknown", quantity=ci.quantity, available=False
            ))
    return Cart(id=cart.id, items=cart_items, price=total)


@app.get("/cart")
def list_carts(
        offset: int = Query(0, ge=0),
        limit: int = Query(10, ge=1),
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
        db: Session = Depends(get_db)
):
    carts = db.query(CartDB).offset(offset).limit(limit).all()
    result = []
    for cart in carts:
        cart_data = get_cart(cart.id, db)
        result.append(cart_data)
    if min_price is not None:
        result = [c for c in result if c.price >= min_price]
    if max_price is not None:
        result = [c for c in result if c.price <= max_price]
    if min_quantity is not None:
        result = [c for c in result if sum(i.quantity for i in c.items) >= min_quantity]
    if max_quantity is not None:
        result = [c for c in result if sum(i.quantity for i in c.items) <= max_quantity]
    return result


@app.post("/cart/{cart_id}/add/{item_id}")
def add_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = db.get(CartDB, cart_id)
    item = db.get(ItemDB, item_id)
    if not cart or not item:
        raise HTTPException(404, "Not found")

    ci = db.query(CartItemDB).filter_by(cart_id=cart_id, item_id=item_id).first()
    if ci:
        ci.quantity += 1
    else:
        ci = CartItemDB(cart_id=cart_id, item_id=item_id)
        db.add(ci)
    db.commit()
    return {"status": "success"}
