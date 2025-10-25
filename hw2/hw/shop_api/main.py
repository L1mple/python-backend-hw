from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.params import Query
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

try:
    # Экспорт метрик Prometheus на /metrics
    from prometheus_fastapi_instrumentator import Instrumentator
except Exception:  # pragma: no cover
    Instrumentator = None  # type: ignore

# SQLAlchemy setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shop.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# SQLAlchemy models
class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)


class Cart(Base):
    __tablename__ = "carts"
    
    id = Column(Integer, primary_key=True, index=True)
    items = relationship("CartItem", back_populates="cart")


class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    quantity = Column(Integer, default=1)
    
    cart = relationship("Cart", back_populates="items")
    item = relationship("Item")


# Create tables
Base.metadata.create_all(bind=engine)


app = FastAPI(title="Shop API")

# Инициализируем /metrics, если доступна библиотека
if Instrumentator is not None:
    Instrumentator().instrument(app).expose(app)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_item_or_404(db: Session, item_id: int) -> Item:
    item = db.query(Item).filter(Item.id == item_id, Item.deleted == False).first()
    if item is None:
        raise HTTPException(status_code=404)
    return item


def _compute_cart_price(db: Session, cart: Cart) -> float:
    total_price = 0.0
    for cart_item in cart.items:
        item = db.query(Item).filter(Item.id == cart_item.item_id, Item.deleted == False).first()
        if item is not None:
            total_price += float(item.price) * int(cart_item.quantity)
    return float(total_price)


def _total_quantity_in_cart(cart: Cart) -> int:
    return int(sum(cart_item.quantity for cart_item in cart.items))


# -----------------
# Item endpoints
# -----------------


@app.post("/item")
def create_item(body: Dict[str, Any], db: Session = Depends(get_db)):
    if not isinstance(body, dict):
        raise HTTPException(status_code=422)

    if "name" not in body or "price" not in body:
        raise HTTPException(status_code=422)

    try:
        item = Item(
            name=body["name"],
            price=float(body["price"]),
            deleted=False,
        )
    except (ValueError, TypeError):
        raise HTTPException(status_code=422)
    db.add(item)
    db.commit()
    db.refresh(item)

    response = JSONResponse(status_code=201, content={
        "id": item.id,
        "name": item.name,
        "price": item.price,
        "deleted": item.deleted,
    })
    return response


@app.get("/item/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = _get_item_or_404(db, item_id)
    return {
        "id": item.id,
        "name": item.name,
        "price": item.price,
        "deleted": item.deleted,
    }


@app.get("/item")
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0.0),
    max_price: Optional[float] = Query(default=None, ge=0.0),
    show_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    query = db.query(Item)
    
    if not show_deleted:
        query = query.filter(Item.deleted == False)
    
    if min_price is not None:
        query = query.filter(Item.price >= float(min_price))
    if max_price is not None:
        query = query.filter(Item.price <= float(max_price))
    
    items = query.offset(offset).limit(limit).all()
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "deleted": item.deleted,
        }
        for item in items
    ]


@app.put("/item/{item_id}")
def replace_item(item_id: int, body: Dict[str, Any], db: Session = Depends(get_db)):
    existing = db.query(Item).filter(Item.id == item_id).first()
    if existing is None:
        raise HTTPException(status_code=404)

    if not isinstance(body, dict) or "name" not in body or "price" not in body:
        raise HTTPException(status_code=422)

    existing.name = body["name"]
    existing.price = float(body["price"])
    db.commit()
    db.refresh(existing)
    
    return {
        "id": existing.id,
        "name": existing.name,
        "price": existing.price,
        "deleted": existing.deleted,
    }


@app.patch("/item/{item_id}")
def patch_item(item_id: int, body: Dict[str, Any], db: Session = Depends(get_db)):
    existing = db.query(Item).filter(Item.id == item_id).first()
    if existing is None:
        raise HTTPException(status_code=404)

    if existing.deleted is True:
        return JSONResponse(status_code=304, content=None)

    if not isinstance(body, dict):
        raise HTTPException(status_code=422)

    allowed_keys = {"name", "price"}
    if any(key not in allowed_keys for key in body.keys()):
        raise HTTPException(status_code=422)
    if "deleted" in body:
        raise HTTPException(status_code=422)

    if "name" in body:
        existing.name = body["name"]
    if "price" in body:
        existing.price = float(body["price"])
    
    db.commit()
    db.refresh(existing)
    
    return {
        "id": existing.id,
        "name": existing.name,
        "price": existing.price,
        "deleted": existing.deleted,
    }


@app.delete("/item/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    existing = db.query(Item).filter(Item.id == item_id).first()
    if existing is None:
        return {"status": "ok"}

    existing.deleted = True
    db.commit()
    return {"status": "ok"}


# -----------------
# Cart endpoints
# -----------------


@app.post("/cart")
def create_cart(db: Session = Depends(get_db)):
    cart = Cart()
    db.add(cart)
    db.commit()
    db.refresh(cart)

    response = JSONResponse(status_code=201, content={"id": cart.id})
    response.headers["Location"] = f"/cart/{cart.id}"
    return response


@app.get("/cart/{cart_id}")
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if cart is None:
        raise HTTPException(status_code=404)

    result = {
        "id": cart.id,
        "items": [
            {
                "id": cart_item.item_id,
                "quantity": cart_item.quantity,
            }
            for cart_item in cart.items
        ],
        "price": _compute_cart_price(db, cart),
    }
    return result


@app.get("/cart")
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0.0),
    max_price: Optional[float] = Query(default=None, ge=0.0),
    min_quantity: Optional[int] = Query(default=None, ge=0),
    max_quantity: Optional[int] = Query(default=None, ge=0),
    db: Session = Depends(get_db),
):
    carts = db.query(Cart).offset(offset).limit(limit).all()

    # Apply filters
    filtered_carts = []
    for cart in carts:
        price = _compute_cart_price(db, cart)
        quantity = _total_quantity_in_cart(cart)
        
        if min_price is not None and price < float(min_price):
            continue
        if max_price is not None and price > float(max_price):
            continue
        if min_quantity is not None and quantity < int(min_quantity):
            continue
        if max_quantity is not None and quantity > int(max_quantity):
            continue
            
        filtered_carts.append(cart)

    result = [
        {
            "id": cart.id,
            "items": [
                {
                    "id": cart_item.item_id,
                    "quantity": cart_item.quantity,
                }
                for cart_item in cart.items
            ],
            "price": _compute_cart_price(db, cart),
        }
        for cart in filtered_carts
    ]
    return result


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if cart is None:
        raise HTTPException(status_code=404)

    item = db.query(Item).filter(Item.id == item_id, Item.deleted == False).first()
    if item is None:
        raise HTTPException(status_code=404)

    # Check if item already in cart
    existing_cart_item = db.query(CartItem).filter(
        CartItem.cart_id == cart_id,
        CartItem.item_id == item_id
    ).first()
    
    if existing_cart_item:
        existing_cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(cart_item)
    
    db.commit()
    return {"id": cart_id}


# -----------------
# WebSocket Chat (extra task)
# -----------------


class ChatRoom:
    def __init__(self) -> None:
        self.connections: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, username: str) -> None:
        await websocket.accept()
        self.connections[websocket] = username

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.pop(websocket, None)

    async def broadcast(self, message: str, sender: Optional[WebSocket] = None) -> None:
        for ws, _ in list(self.connections.items()):
            if sender is not None and ws is sender:
                # Отправляем всем, кроме отправителя
                continue
            try:
                await ws.send_text(message)
            except Exception:
                # Если клиент умер, удаляем
                self.disconnect(ws)


rooms: Dict[str, ChatRoom] = {}


def _get_or_create_room(chat_name: str) -> ChatRoom:
    room = rooms.get(chat_name)
    if room is None:
        room = ChatRoom()
        rooms[chat_name] = room
    return room


def _generate_username() -> str:
    # Простая генерация имени пользователя
    from uuid import uuid4

    return f"user-{uuid4().hex[:6]}"


@app.websocket("/chat/{chat_name}")
async def websocket_chat(websocket: WebSocket, chat_name: str):
    room = _get_or_create_room(chat_name)
    username = _generate_username()

    await room.connect(websocket, username)
    try:
        while True:
            message = await websocket.receive_text()
            formatted = f"{username} :: {message}"
            await room.broadcast(formatted, sender=websocket)
    except WebSocketDisconnect:
        room.disconnect(websocket)
    except Exception:
        room.disconnect(websocket)