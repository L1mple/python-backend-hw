from fastapi import FastAPI, HTTPException, Query, Path, Response, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from prometheus_fastapi_instrumentator import Instrumentator

from sqlalchemy import (
    create_engine, Integer, String, Float, Boolean, ForeignKey, select
)
from sqlalchemy.orm import (
    declarative_base, Mapped, mapped_column, relationship,
    sessionmaker, Session
)
import os

# FastAPI + metrics
app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

# DB setup
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://user:password@db:5432/hw2_db",
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# ORM models
class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    cart_items: Mapped[List["CartItem"]] = relationship(back_populates="item", cascade="all, delete-orphan")

class Cart(Base):
    __tablename__ = "carts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    items: Mapped[List["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan")

class CartItem(Base):
    __tablename__ = "cart_items"
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    cart: Mapped["Cart"] = relationship(back_populates="items")
    item: Mapped["Item"] = relationship(back_populates="cart_items")

# Create tables at import (как было)
Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schemas
class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0.0)

class ItemPut(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0.0)

class ItemPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, ge=0.0)
    class Config:
        extra = "forbid"

class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

class CartItemOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    price: float

# utils
def get_item_or_404(db: Session, item_id: int, allow_deleted: bool = False) -> Item:
    it = db.get(Item, item_id)
    if not it or (it.deleted and not allow_deleted):
        raise HTTPException(404, "Item not found")
    return it

def get_cart_or_404(db: Session, cart_id: int) -> Cart:
    cart = db.get(Cart, cart_id)
    if not cart:
        raise HTTPException(404, "Cart not found")
    return cart

def cart_snapshot(db: Session, cart_id: int) -> CartOut:
    cart = get_cart_or_404(db, cart_id)
    stmt = (
        select(CartItem, Item)
        .select_from(CartItem)
        .join(Item, Item.id == CartItem.item_id)
        .where(CartItem.cart_id == cart.id)
    )
    items_out: List[CartItemOut] = []
    total = 0.0
    for ci, it in db.execute(stmt).all():
        items_out.append(
            CartItemOut(
                id=it.id,
                name=it.name,
                quantity=ci.quantity,
                available=not it.deleted,
            )
        )
        total += float(it.price) * ci.quantity
    return CartOut(id=cart.id, items=items_out, price=total)

# cart endpoints
@app.post("/cart", status_code=201)
def create_cart(response: Response, db: Session = Depends(get_db)):
    cart = Cart()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    response.headers["Location"] = f"/cart/{cart.id}"
    return {"id": cart.id}

@app.get("/cart/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    return cart_snapshot(db, cart_id)

@app.get("/cart", response_model=List[CartOut])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    result: List[CartOut] = []
    for cart_id_value, in db.execute(select(Cart.id).order_by(Cart.id)).all():
        snap = cart_snapshot(db, cart_id_value)
        qty = sum(ci.quantity for ci in snap.items)
        if min_quantity is not None and qty < min_quantity:
            continue
        if max_quantity is not None and qty > max_quantity:
            continue
        if min_price is not None and snap.price < min_price:
            continue
        if max_price is not None and snap.price > max_price:
            continue
        result.append(snap)
    return result[offset: offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}", response_model=CartOut)
def add_to_cart(
    cart_id: int = Path(..., ge=1),
    item_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    cart = get_cart_or_404(db, cart_id)
    it = get_item_or_404(db, item_id, allow_deleted=True)
    if it.deleted:
        raise HTTPException(400, "Cannot add a deleted item to cart")

    existing_ci = db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.item_id == it.id,
        )
    ).scalar_one_or_none()

    if existing_ci is not None:
        existing_ci.quantity += 1
    else:
        db.add(CartItem(cart_id=cart.id, item_id=it.id, quantity=1))

    db.commit()
    return cart_snapshot(db, cart_id)

# item endpoints
@app.post("/item", response_model=ItemOut, status_code=201)
def create_item(body: ItemCreate, db: Session = Depends(get_db)):
    it = Item(name=body.name, price=float(body.price), deleted=False)
    db.add(it)
    db.commit()
    db.refresh(it)
    return ItemOut(id=it.id, name=it.name, price=it.price, deleted=it.deleted)

@app.get("/item/{item_id}", response_model=ItemOut)
def get_item(item_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    it = get_item_or_404(db, item_id)
    return ItemOut(id=it.id, name=it.name, price=it.price, deleted=it.deleted)

@app.get("/item", response_model=List[ItemOut])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
    db: Session = Depends(get_db),
):
    stmt = select(Item).order_by(Item.id)
    items = [it for (it,) in db.execute(stmt).all()]
    out: List[ItemOut] = []
    for it in items:
        if not show_deleted and it.deleted:
            continue
        if min_price is not None and float(it.price) < min_price:
            continue
        if max_price is not None and float(it.price) > max_price:
            continue
        out.append(ItemOut(id=it.id, name=it.name, price=it.price, deleted=it.deleted))
    return out[offset: offset + limit]

@app.put("/item/{item_id}", response_model=ItemOut)
def put_item(item_id: int = Path(..., ge=1), body: ItemPut = ..., db: Session = Depends(get_db)):
    it = get_item_or_404(db, item_id)
    it.name = body.name
    it.price = float(body.price)
    db.commit()
    db.refresh(it)
    return ItemOut(id=it.id, name=it.name, price=it.price, deleted=it.deleted)

@app.patch("/item/{item_id}", response_model=ItemOut)
def patch_item(item_id: int = Path(..., ge=1), body: ItemPatch = ..., db: Session = Depends(get_db)):
    it = get_item_or_404(db, item_id, allow_deleted=True)
    if it.deleted:
        return Response(status_code=304)
    if body.name is not None:
        it.name = body.name
    if body.price is not None:
        it.price = float(body.price)
    db.commit()
    db.refresh(it)
    return ItemOut(id=it.id, name=it.name, price=it.price, deleted=it.deleted)

@app.delete("/item/{item_id}")
def delete_item(item_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    it = get_item_or_404(db, item_id, allow_deleted=True)
    it.deleted = True
    db.commit()
    return {}
