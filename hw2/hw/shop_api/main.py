from __future__ import annotations

from fastapi import FastAPI, HTTPException, Path, Query, Response, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from typing import Dict, List, Optional
from http import HTTPStatus
import asyncio
from uuid import uuid4
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from shop_api.database import init_db, get_session, Item as ItemDB, Cart as CartDB, CartItem as CartItemDB

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Shop API", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)

class ItemCreate(BaseModel):
    name: str
    price: float = Field(..., ge=0)

class ItemPut(BaseModel):
    name: str
    price: float = Field(..., ge=0)

class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)

    @model_validator(mode="before")
    def forbid_deleted_and_unknown(cls, data):
        if not isinstance(data, dict):
            return data
        if "deleted" in data:
            raise ValueError("Field 'deleted' cannot be patched")
        allowed = {"name", "price"}
        unknown = set(data.keys()) - allowed
        if unknown:
            raise ValueError(f"Unknown fields in PATCH: {unknown}")
        return data

class CartItemView(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartView(BaseModel):
    id: int
    items: List[CartItemView]
    price: float

async def _get_item(item_id: int, session: AsyncSession) -> ItemDB:
    result = await session.execute(select(ItemDB).where(ItemDB.id == item_id))
    item = result.scalar_one_or_none()
    if item is None or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item

async def _build_cart_view(cart_id: int, session: AsyncSession) -> CartView:
    # Check if cart exists
    cart_result = await session.execute(select(CartDB).where(CartDB.id == cart_id))
    cart = cart_result.scalar_one_or_none()
    if cart is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    
    # Get cart items with their details
    cart_items_result = await session.execute(
        select(CartItemDB, ItemDB)
        .join(ItemDB, CartItemDB.item_id == ItemDB.id, isouter=True)
        .where(CartItemDB.cart_id == cart_id)
    )
    cart_items = cart_items_result.all()
    
    items_view: List[CartItemView] = []
    total_price = 0.0
    
    for cart_item, item in cart_items:
        available = bool(item and not item.deleted)
        name = item.name if item else f"item#{cart_item.item_id}"
        items_view.append(CartItemView(
            id=cart_item.item_id,
            name=name,
            quantity=cart_item.quantity,
            available=available
        ))
        if available and item is not None:
            total_price += item.price * cart_item.quantity
    
    return CartView(id=cart_id, items=items_view, price=float(total_price))

@app.post("/item", status_code=HTTPStatus.CREATED)
async def create_item(payload: ItemCreate, response: Response, session: AsyncSession = Depends(get_session)):
    item = ItemDB(name=payload.name, price=float(payload.price), deleted=False)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    response.headers["location"] = f"/item/{item.id}"
    return {"id": item.id, "name": item.name, "price": item.price, "deleted": item.deleted}

@app.get("/item/{item_id}")
async def get_item(item_id: int = Path(..., ge=1), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemDB).where(ItemDB.id == item_id))
    item = result.scalar_one_or_none()
    if item is None or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return {"id": item.id, "name": item.name, "price": item.price, "deleted": item.deleted}

@app.get("/item")
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False),
    session: AsyncSession = Depends(get_session)
):
    query = select(ItemDB)
    
    if not show_deleted:
        query = query.where(ItemDB.deleted == False)
    
    if min_price is not None:
        query = query.where(ItemDB.price >= min_price)
    
    if max_price is not None:
        query = query.where(ItemDB.price <= max_price)
    
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    return [{"id": i.id, "name": i.name, "price": i.price, "deleted": i.deleted} for i in items]

@app.put("/item/{item_id}")
async def put_item(
    item_id: int = Path(..., ge=1),
    payload: ItemPut = ...,
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(ItemDB).where(ItemDB.id == item_id))
    existing = result.scalar_one_or_none()
    if existing is None or existing.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    existing.name = payload.name
    existing.price = float(payload.price)
    await session.commit()
    await session.refresh(existing)
    
    return {"id": existing.id, "name": existing.name, "price": existing.price, "deleted": existing.deleted}

@app.patch("/item/{item_id}")
async def patch_item(
    item_id: int = Path(..., ge=1),
    payload: ItemPatch = ...,
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(ItemDB).where(ItemDB.id == item_id))
    existing = result.scalar_one_or_none()
    if existing is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    if existing.deleted:
        return JSONResponse(status_code=HTTPStatus.NOT_MODIFIED, content=None)
    
    if payload.name is not None:
        existing.name = payload.name
    if payload.price is not None:
        existing.price = float(payload.price)
    
    await session.commit()
    await session.refresh(existing)
    
    return {"id": existing.id, "name": existing.name, "price": existing.price, "deleted": existing.deleted}

@app.delete("/item/{item_id}")
async def delete_item(item_id: int = Path(..., ge=1), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemDB).where(ItemDB.id == item_id))
    existing = result.scalar_one_or_none()
    if existing is None:
        return {"status": "ok"}
    
    if not existing.deleted:
        existing.deleted = True
        await session.commit()
    
    return {"status": "ok"}

@app.post("/cart", status_code=HTTPStatus.CREATED)
async def create_cart(response: Response, session: AsyncSession = Depends(get_session)):
    cart = CartDB()
    session.add(cart)
    await session.commit()
    await session.refresh(cart)
    response.headers["location"] = f"/cart/{cart.id}"
    return {"id": cart.id}

@app.get("/cart/{cart_id}")
async def get_cart(cart_id: int = Path(..., ge=1), session: AsyncSession = Depends(get_session)):
    view = await _build_cart_view(cart_id, session)
    return view.model_dump()

@app.get("/cart")
async def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    session: AsyncSession = Depends(get_session)
):
    # Get all carts
    result = await session.execute(select(CartDB))
    carts = result.scalars().all()
    
    # Build views for all carts
    views = []
    for cart in carts:
        view = await _build_cart_view(cart.id, session)
        views.append(view)
    
    # Apply filters
    if min_price is not None:
        views = [v for v in views if v.price >= min_price]
    if max_price is not None:
        views = [v for v in views if v.price <= max_price]
    
    def qty(v: CartView) -> int:
        return sum(item.quantity for item in v.items)
    
    if min_quantity is not None:
        views = [v for v in views if qty(v) >= min_quantity]
    if max_quantity is not None:
        views = [v for v in views if qty(v) <= max_quantity]
    
    # Apply pagination
    views = views[offset : offset + limit]
    
    return [v.model_dump() for v in views]

@app.post("/cart/{cart_id}/add/{item_id}")
async def cart_add_item(
    cart_id: int = Path(..., ge=1),
    item_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session)
):
    # Check if cart exists
    cart_result = await session.execute(select(CartDB).where(CartDB.id == cart_id))
    cart = cart_result.scalar_one_or_none()
    if cart is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    
    # Check if item exists and is not deleted
    item_result = await session.execute(select(ItemDB).where(ItemDB.id == item_id))
    item = item_result.scalar_one_or_none()
    if item is None or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    # Check if item is already in cart
    cart_item_result = await session.execute(
        select(CartItemDB).where(
            and_(CartItemDB.cart_id == cart_id, CartItemDB.item_id == item_id)
        )
    )
    cart_item = cart_item_result.scalar_one_or_none()
    
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItemDB(cart_id=cart_id, item_id=item_id, quantity=1)
        session.add(cart_item)
    
    await session.commit()
    
    view = await _build_cart_view(cart_id, session)
    return view.model_dump()

# WebSocket chat functionality
_rooms: dict[str, set[WebSocket]] = {}
_usernames: dict[WebSocket, str] = {}
_rooms_lock = asyncio.Lock()

def _make_username() -> str:
    return f"user-{uuid4().hex[:6]}"

async def _join_room(room: str, ws: WebSocket):
    async with _rooms_lock:
        _rooms.setdefault(room, set()).add(ws)

async def _leave_room(room: str, ws: WebSocket):
    async with _rooms_lock:
        peers = _rooms.get(room)
        if peers is not None:
            peers.discard(ws)
            if not peers:
                _rooms.pop(room, None)
        _usernames.pop(ws, None)

@app.websocket("/chat/{chat_name}")
async def chat_ws(websocket: WebSocket, chat_name: str):
    await websocket.accept()
    username = _make_username()
    _usernames[websocket] = username
    await _join_room(chat_name, websocket)
    try:
        while True:
            text = await websocket.receive_text()
            peers = _rooms.get(chat_name, set()).copy()
            for peer in peers:
                if peer is websocket:
                    continue
                try:
                    await peer.send_text(f"{username} :: {text}")
                except RuntimeError:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        await _leave_room(chat_name, websocket)
