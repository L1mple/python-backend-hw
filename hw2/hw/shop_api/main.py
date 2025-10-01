from typing import Optional, List, Tuple
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, Query, status, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import (
    create_engine, Integer, String, DECIMAL, Boolean,
    ForeignKey, select, func
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, Session, sessionmaker, relationship
)
from faker import Faker


# ---------- DB setup ----------
DATABASE_URL = "sqlite:///./shop.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

# ---------- MODELS ----------
class Item(Base):
    __tablename__ = "item"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

class Cart(Base):
    __tablename__ = "cart"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    items: Mapped[List["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan")

class CartItem(Base):
    __tablename__ = "cart_item"
    cart_id: Mapped[int] = mapped_column(ForeignKey("cart.id"), primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cart: Mapped[Cart] = relationship(back_populates="items")
    item: Mapped[Item] = relationship()

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- SCHEMAS ----------
class ItemBase(BaseModel):
    name: str = Field(..., max_length=255)
    price: float
    deleted: bool = False

class ItemCreate(ItemBase):
    pass

# PATCH: запрещаем лишние поля и поле deleted
class ItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, max_length=255)
    price: Optional[float] = None

class ItemOut(ItemBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class CartItemOut(BaseModel):
    id: int
    quantity: int

class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    price: float

# ---------- APP ----------
app = FastAPI(title="Shop API")

# ---------- /item ----------
@app.post("/item", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    item = Item(name=payload.name, price=Decimal(str(payload.price)), deleted=payload.deleted)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@app.get("/item", response_model=List[ItemOut])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, gt=0, le=1000),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
    db: Session = Depends(get_db),
):
    stmt = select(Item)
    if not show_deleted:
        stmt = stmt.where(Item.deleted.is_(False))
    if min_price is not None:
        stmt = stmt.where(Item.price >= Decimal(str(min_price)))
    if max_price is not None:
        stmt = stmt.where(Item.price <= Decimal(str(max_price)))
    stmt = stmt.offset(offset).limit(limit)
    return list(db.scalars(stmt))

@app.get("/item/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.put("/item/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemCreate, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    item.name = payload.name
    item.price = Decimal(str(payload.price))
    item.deleted = payload.deleted
    db.commit()
    db.refresh(item)
    return item

@app.patch("/item/{item_id}", response_model=ItemOut)
def patch_item(item_id: int, payload: ItemPatch, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.deleted:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
    if payload.name is not None:
        item.name = payload.name
    if payload.price is not None:
        item.price = Decimal(str(payload.price))
    db.commit()
    db.refresh(item)
    return item

@app.delete("/item/{item_id}", status_code=status.HTTP_200_OK)
def soft_delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Item, item_id)
    if item and not item.deleted:
        item.deleted = True
        db.commit()
    return {"status": "ok"}

# ---------- cart ----------
def _cart_items(db: Session, cart_id: int) -> List[CartItemOut]:
    rows = db.execute(select(CartItem.item_id, CartItem.quantity)
                      .where(CartItem.cart_id == cart_id)).all()
    return [CartItemOut(id=i, quantity=q) for i, q in rows]

def _cart_price(db: Session, cart_id: int) -> float:
    total = db.execute(
        select(func.sum(CartItem.quantity * Item.price))
        .join(Item, Item.id == CartItem.item_id)
        .where(CartItem.cart_id == cart_id, Item.deleted.is_(False))
    ).scalar()
    return float(total or 0.0)

@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart(db: Session = Depends(get_db)):
    cart = Cart()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return Response(
        content=f'{{"id": {cart.id}}}',
        media_type="application/json",
        headers={"location": f"/cart/{cart.id}"},
        status_code=status.HTTP_201_CREATED,
    )

@app.post("/cart/{cart_id}/add/{item_id}", status_code=status.HTTP_200_OK)
def add_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = db.get(Cart, cart_id)
    item = db.get(Item, item_id)
    if cart is None or item is None:
        raise HTTPException(status_code=404, detail="Not found")
    ci = db.get(CartItem, {"cart_id": cart_id, "item_id": item_id})
    if ci:
        ci.quantity += 1
    else:
        ci = CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(ci)
    db.commit()
    return {"status": "ok"}

@app.get("/cart/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = db.get(Cart, cart_id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    return CartOut(id=cart.id, items=_cart_items(db, cart.id), price=_cart_price(db, cart.id))

@app.get("/cart", response_model=List[CartOut])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, gt=0, le=1000),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    carts = list(db.scalars(select(Cart).offset(offset).limit(limit)))
    result: List[CartOut] = []
    for c in carts:
        items = _cart_items(db, c.id)
        qty = sum(it.quantity for it in items)
        price = _cart_price(db, c.id)
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue
        if min_quantity is not None and qty < min_quantity:
            continue
        if max_quantity is not None and qty > max_quantity:
            continue
        result.append(CartOut(id=c.id, items=items, price=price))
    return result

# ---------- WS ----------

faker = Faker()
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[Tuple[WebSocket, str]]] = {}

    async def connect(self, chat_name: str, ws: WebSocket):
        new_user = faker.name()
        await ws.accept()
        if chat_name not in self.active_connections:
            self.active_connections[chat_name] = []
        self.active_connections[chat_name].append((ws, new_user))
        return new_user

    def disconnect(self, chat_name: str, ws: WebSocket):
        if chat_name in self.active_connections:
            self.active_connections[chat_name] = [
                (ws, user) for (ws, user) in self.active_connections[chat_name] if ws != ws
            ]
            if not self.active_connections[chat_name]:
                del self.active_connections[chat_name]

    async def broadcast(self, chat_name: str, sender_ws: WebSocket, message: str) -> None:
        conns = self.active_connections.get(chat_name, [])
        username = next((u for (ws, u) in conns if ws == sender_ws), "Anon")
        full_msg = f"{username} :: {message}"
        for ws, _ in conns:
            if ws != sender_ws:
                await ws.send_text(full_msg)

manager = ConnectionManager()


@app.websocket("/chat/{chat_name}")
async def websocket_endpoint(ws: WebSocket, chat_name: str):
    username = await manager.connect(chat_name, ws)
    try:
        while True:
            data = await ws.receive_text()
            await manager.broadcast(chat_name, ws, data)
    except WebSocketDisconnect:
        manager.disconnect(chat_name, ws)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("shop_api.main:app", host="127.0.0.1", port=3000, reload=True)