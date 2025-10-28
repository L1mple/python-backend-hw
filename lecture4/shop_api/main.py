from fastapi import FastAPI, Query, HTTPException, Response, Depends
from pydantic import BaseModel
from typing import Optional, List

from sqlalchemy import create_engine, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy.orm import mapped_column, relationship, sessionmaker, Session

class Base(DeclarativeBase):
    pass

class ItemDB(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable = True)
    price: Mapped[float] = mapped_column(nullable = True)
    deleted: Mapped[bool] = mapped_column(nullable = True)

class CartDB(Base):
    __tablename__ = "carts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    items = relationship("CartItemDB", back_populates="cart", cascade="all, delete-orphan")

class CartItemDB(Base):
    __tablename__ = "cart_items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)

    cart = relationship("CartDB", back_populates="items")
    item = relationship("ItemDB")

engine = create_engine(
    "sqlite:///file:memdb1?mode=memory&cache=shared", 
    echo=True,
    connect_args={"check_same_thread": False, "uri": True}
)

SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base.metadata.create_all(engine)

app = FastAPI(title="Shop API")

class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool

class ItemCreate(BaseModel):
    name: str
    price: float

class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    
    model_config = {"extra": "forbid"}

class ItemPut(BaseModel):
    name: str
    price: float
    deleted: Optional[bool] = None

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class Cart(BaseModel):
    id: int
    items: List[CartItem] = []
    price: float = 0.0


@app.post('/item', status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    new_item = ItemDB(name=item.name, price=item.price, deleted=False)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return Item(id=new_item.id, name=new_item.name, price=new_item.price, deleted=new_item.deleted)

@app.get('/item/{item_id}')
def get_item(item_id:int, db: Session = Depends(get_db)):
    new_item = db.get(ItemDB, item_id)
    if not new_item or new_item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return Item(id=new_item.id, name=new_item.name, price=new_item.price, deleted=new_item.deleted)

@app.get("/item")
def get_item_list(
    limit: Optional[int] = Query(default=10, ge=1),
    offset: Optional[int] = Query(default=0, ge=0),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    show_deleted: Optional[bool] = False,
    db: Session = Depends(get_db),
):
    query = select(ItemDB)
    if not show_deleted:
        query = query.where(ItemDB.deleted == False)
    if min_price is not None:
        query = query.where(ItemDB.price >= min_price)
    if max_price is not None:
        query = query.where(ItemDB.price <= max_price)

    query = query.offset(offset).limit(limit)
    rows = db.execute(query).scalars().all()

    return [Item(id=r.id, name=r.name, price=r.price, deleted=r.deleted) for r in rows]


@app.put("/item/{item_id}")
def put_item(item_id: int, item: ItemPut, db: Session = Depends(get_db)):
    db_item = db.get(ItemDB, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.name = item.name
    db_item.price = item.price
    if item.deleted is not None:
        db_item.deleted = item.deleted
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return Item(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)


@app.patch("/item/{item_id}")
def patch_item(item_id: int, item: ItemPatch, db: Session = Depends(get_db)):
    db_item = db.get(ItemDB, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    if db_item.deleted:
        # Item marked as deleted -> not modifiable via PATCH
        raise HTTPException(status_code=304, detail="Item is deleted")

    if item.price is not None:
        db_item.price = item.price
    if item.name is not None:
        db_item.name = item.name

    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return Item(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)


@app.delete("/item/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.get(ItemDB, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.deleted = True
    db.add(db_item)
    db.commit()
    return Response(status_code=200)


# --- Cart endpoints ---


def cart_to_schema(db: Session, cart: CartDB) -> Cart:
    items: List[CartItem] = []
    total_price = 0.0
    for ci in cart.items:
        item = db.get(ItemDB, ci.item_id)
        available = False
        name = ""
        price = 0.0
        if item:
            available = not item.deleted
            name = item.name
            price = item.price
        items.append(CartItem(id=ci.item_id, name=name, quantity=ci.quantity, available=available))
        if item and not item.deleted:
            total_price += price * ci.quantity

    return Cart(id=cart.id, items=items, price=total_price)


@app.post("/cart", status_code=201)
def create_cart(response: Response, db: Session = Depends(get_db)):
    cart = CartDB()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    response.headers["location"] = f"/cart/{cart.id}"
    return cart_to_schema(db, cart)


@app.get("/cart/{cart_id}")
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = db.get(CartDB, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart_to_schema(db, cart)


@app.get("/cart")
def get_cart_list(
    limit: Optional[int] = Query(default=10, ge=1),
    offset: Optional[int] = Query(default=0, ge=0),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    min_quantity: Optional[int] = Query(default=None, ge=0),
    max_quantity: Optional[int] = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    # Build list of carts and apply filters in Python (small dataset for tests)
    carts = db.execute(select(CartDB)).scalars().all()
    result = []
    for cart in carts:
        schema = cart_to_schema(db, cart)
        result.append(schema)

    if min_price is not None:
        result = [c for c in result if c.price >= min_price]
    if max_price is not None:
        result = [c for c in result if c.price <= max_price]
    if min_quantity is not None:
        result = [c for c in result if sum(i.quantity for i in c.items) >= min_quantity]
    if max_quantity is not None:
        result = [c for c in result if sum(i.quantity for i in c.items) <= max_quantity]

    # Apply offset/limit
    return result[offset : offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = db.get(CartDB, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    item = db.get(ItemDB, item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")

    # find existing cart item
    cart_item = db.execute(
        select(CartItemDB).where(CartItemDB.cart_id == cart_id, CartItemDB.item_id == item_id)
    ).scalar_one_or_none()

    if cart_item:
        cart_item.quantity = cart_item.quantity + 1
        db.add(cart_item)
    else:
        cart_item = CartItemDB(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(cart_item)

    db.commit()
    db.refresh(cart)
    return cart_to_schema(db, cart)
