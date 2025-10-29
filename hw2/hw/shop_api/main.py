from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from uuid import uuid4
import time
import os
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, func, select, case
from sqlalchemy.orm import declarative_base, sessionmaker


app = FastAPI(title="Shop API")

# --- Database configuration (HW4) ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shop.db")
_engine_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True, echo=False, connect_args=_engine_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
Base = declarative_base()

class ItemModel(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

class CartModel(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, autoincrement=True)

class CartItemModel(Base):
    __tablename__ = "cart_items"
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="RESTRICT"), primary_key=True)
    quantity = Column(Integer, nullable=False, default=1)

try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

@app.on_event("startup")
def _create_tables_on_startup() -> None:
    Base.metadata.create_all(bind=engine)


# Prometheus metrics
REQUEST_COUNT = Counter('shop_api_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('shop_api_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
ITEMS_CREATED = Counter('shop_api_items_created_total', 'Total items created')
CARTS_CREATED = Counter('shop_api_carts_created_total', 'Total carts created')


# In-memory storage
_items: Dict[int, Dict[str, Any]] = {}
_item_id_seq: int = 1

_carts: Dict[int, Dict[str, Any]] = {}
_cart_id_seq: int = 1


# Models
class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(...)
    price: float = Field(..., ge=0)


class ItemPut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(...)
    price: float = Field(..., ge=0)


class ItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)


def _cart_price_db(db, cart_id: int) -> float:
    result = db.execute(
        select(func.coalesce(func.sum(CartItemModel.quantity * ItemModel.price), 0.0))
        .join(ItemModel, CartItemModel.item_id == ItemModel.id)
        .where(CartItemModel.cart_id == cart_id, ItemModel.deleted.is_(False))
    ).scalar_one()
    return float(result or 0.0)


def _cart_items_view(db, cart_id: int) -> List[Dict[str, Any]]:
    rows = db.execute(
        select(CartItemModel.item_id, CartItemModel.quantity, ItemModel.name, ItemModel.deleted)
        .join(ItemModel, CartItemModel.item_id == ItemModel.id, isouter=True)
        .where(CartItemModel.cart_id == cart_id)
    ).all()
    items: List[Dict[str, Any]] = []
    for item_id, quantity, name, deleted in rows:
        available = (name is not None) and (not bool(deleted))
        items.append({"id": item_id, "name": name, "quantity": int(quantity), "available": available})
    return items


def _cart_total_quantity_db(db, cart_id: int) -> int:
    result = db.execute(
        select(func.coalesce(func.sum(CartItemModel.quantity), 0)).where(CartItemModel.cart_id == cart_id)
    ).scalar_one()
    return int(result or 0)


# Cart endpoints
@app.post("/cart")
def create_cart(response: Response) -> Dict[str, int]:
    with SessionLocal() as db:
        cart = CartModel()
        db.add(cart)
        db.flush()
        response.headers["location"] = f"/cart/{cart.id}"
        response.status_code = 201
        CARTS_CREATED.inc()
        db.commit()
        return {"id": cart.id}


@app.get("/cart/{cart_id}")
def get_cart(cart_id: int) -> Dict[str, Any]:
    with SessionLocal() as db:
        cart = db.get(CartModel, cart_id)
        if cart is None:
            raise HTTPException(status_code=404)
        items = _cart_items_view(db, cart_id)
        price = _cart_price_db(db, cart_id)
        return {"id": cart_id, "items": items, "price": price}


@app.get("/cart")
def get_cart_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
) -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        price_case = case((ItemModel.deleted.is_(False), ItemModel.price), else_=0.0)
        rows = db.execute(
            select(
                CartModel.id.label("id"),
                func.coalesce(func.sum(CartItemModel.quantity * price_case), 0.0).label("price"),
                func.coalesce(func.sum(CartItemModel.quantity), 0).label("quantity"),
            )
            .outerjoin(CartItemModel, CartItemModel.cart_id == CartModel.id)
            .outerjoin(ItemModel, ItemModel.id == CartItemModel.item_id)
            .group_by(CartModel.id)
        ).all()
        views = [
            {"id": r.id, "price": float(r.price or 0.0), "_quantity": int(r.quantity or 0)} for r in rows
        ]
        if min_price is not None:
            views = [v for v in views if v["price"] >= min_price]
        if max_price is not None:
            views = [v for v in views if v["price"] <= max_price]
        if min_quantity is not None:
            views = [v for v in views if v["_quantity"] >= min_quantity]
        if max_quantity is not None:
            views = [v for v in views if v["_quantity"] <= max_quantity]
        views = views[offset : offset + limit]
        result: List[Dict[str, Any]] = []
        for v in views:
            items = _cart_items_view(db, v["id"])
            result.append({"id": v["id"], "items": items, "price": v["price"]})
        return result


@app.post("/cart/{cart_id}/add/{item_id}")
def add_to_cart(cart_id: int, item_id: int) -> Dict[str, Any]:
    with SessionLocal() as db:
        cart = db.get(CartModel, cart_id)
        if cart is None:
            raise HTTPException(status_code=404)
        item = db.get(ItemModel, item_id)
        if item is None or item.deleted:
            raise HTTPException(status_code=404)
        ci = db.get(CartItemModel, (cart_id, item_id))
        if ci:
            ci.quantity = int(ci.quantity) + 1
        else:
            db.add(CartItemModel(cart_id=cart_id, item_id=item_id, quantity=1))
        db.commit()
        return {"id": cart_id}


# Item endpoints
@app.post("/item")
def create_item(item: ItemCreate, response: Response) -> Dict[str, Any]:
    with SessionLocal() as db:
        m = ItemModel(name=item.name, price=float(item.price), deleted=False)
        db.add(m)
        db.flush()
        response.status_code = 201
        ITEMS_CREATED.inc()
        db.commit()
        return {"id": m.id, "name": m.name, "price": float(m.price), "deleted": bool(m.deleted)}


@app.get("/item/{item_id}")
def get_item(item_id: int) -> Dict[str, Any]:
    with SessionLocal() as db:
        m = db.get(ItemModel, item_id)
        if m is None or m.deleted:
            raise HTTPException(status_code=404)
        return {"id": m.id, "name": m.name, "price": float(m.price), "deleted": bool(m.deleted)}


@app.get("/item")
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
) -> List[Dict[str, Any]]:
    with SessionLocal() as db:
        q = select(ItemModel)
        if not show_deleted:
            q = q.where(ItemModel.deleted.is_(False))
        if min_price is not None:
            q = q.where(ItemModel.price >= float(min_price))
        if max_price is not None:
            q = q.where(ItemModel.price <= float(max_price))
        q = q.offset(offset).limit(limit)
        rows = db.execute(q).scalars().all()
        return [
            {"id": m.id, "name": m.name, "price": float(m.price), "deleted": bool(m.deleted)} for m in rows
        ]


@app.put("/item/{item_id}")
def put_item(item_id: int, body: ItemPut) -> Dict[str, Any]:
    with SessionLocal() as db:
        m = db.get(ItemModel, item_id)
        if m is None or m.deleted:
            raise HTTPException(status_code=404)
        m.name = body.name
        m.price = float(body.price)
        db.commit()
        return {"id": m.id, "name": m.name, "price": float(m.price), "deleted": bool(m.deleted)}


@app.patch("/item/{item_id}")
def patch_item(item_id: int, body: ItemPatch) -> Dict[str, Any]:
    with SessionLocal() as db:
        m = db.get(ItemModel, item_id)
        if m is None:
            raise HTTPException(status_code=404)
        if m.deleted:
            return Response(status_code=304)
        if body.name is not None:
            m.name = body.name
        if body.price is not None:
            m.price = float(body.price)
        db.commit()
        return {"id": m.id, "name": m.name, "price": float(m.price), "deleted": bool(m.deleted)}


@app.delete("/item/{item_id}")
def delete_item(item_id: int) -> Dict[str, Any]:
    with SessionLocal() as db:
        m = db.get(ItemModel, item_id)
        if m is None:
            raise HTTPException(status_code=404)
        m.deleted = True
        db.commit()
        return {"id": item_id}


# --- WebSocket Chat rooms ---
@dataclass(slots=True)
class Room:
    name: str
    subscribers: List[WebSocket] = field(init=False, default_factory=list)

    async def subscribe(self, ws: WebSocket) -> None:
        await ws.accept()
        self.subscribers.append(ws)

    def unsubscribe(self, ws: WebSocket) -> None:
        if ws in self.subscribers:
            self.subscribers.remove(ws)

    async def publish(self, message: str) -> None:
        for ws in list(self.subscribers):
            try:
                await ws.send_text(message)
            except Exception:
                self.unsubscribe(ws)


@dataclass(slots=True)
class ChatHub:
    rooms: Dict[str, Room] = field(init=False, default_factory=dict)

    def get_room(self, name: str) -> Room:
        room = self.rooms.get(name)
        if room is None:
            room = Room(name=name)
            self.rooms[name] = room
        return room


_chat_hub = ChatHub()


@app.websocket("/chat/{chat_name}")
async def ws_chat(chat_name: str, ws: WebSocket):
    room = _chat_hub.get_room(chat_name)
    client_id = str(uuid4())[:8]
    await room.subscribe(ws)
    await room.publish(f"[{chat_name}] client {client_id} joined")
    try:
        while True:
            text = await ws.receive_text()
            await room.publish(f"{client_id}::{text}")
    except WebSocketDisconnect:
        room.unsubscribe(ws)
        await room.publish(f"[{chat_name}] client {client_id} left")


# Middleware for metrics
@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    method = request.method
    endpoint = request.url.path
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=response.status_code).inc()
    
    return response

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Prometheus metrics endpoint
@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
