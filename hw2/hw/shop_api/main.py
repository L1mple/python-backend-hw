from __future__ import annotations

from fastapi import FastAPI, HTTPException, Path, Query, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator
from typing import Dict, List, Optional
from http import HTTPStatus
import itertools, asyncio
from uuid import uuid4
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

class ItemModel(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

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

_items: Dict[int, ItemModel] = {}
_item_id_counter = itertools.count(1)
_carts: Dict[int, Dict[int, int]] = {}
_cart_id_counter = itertools.count(1)

def _get_item(item_id: int) -> ItemModel:
    item = _items.get(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item

def _build_cart_view(cart_id: int) -> CartView:
    if cart_id not in _carts:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    items_view: List[CartItemView] = []
    total_price = 0.0
    for iid, qty in _carts[cart_id].items():
        stored = _items.get(iid)
        available = bool(stored and not stored.deleted)
        name = stored.name if stored else f"item#{iid}"
        items_view.append(CartItemView(id=iid, name=name, quantity=qty, available=available))
        if available and stored is not None:
            total_price += stored.price * qty
    return CartView(id=cart_id, items=items_view, price=float(total_price))

def _cart_total_quantity(cart_id: int) -> int:
    return sum(_carts.get(cart_id, {}).values())

@app.post("/item", status_code=HTTPStatus.CREATED)
def create_item(payload: ItemCreate, response: Response):
    new_id = next(_item_id_counter)
    item = ItemModel(id=new_id, name=payload.name, price=float(payload.price), deleted=False)
    _items[new_id] = item
    response.headers["location"] = f"/item/{new_id}"
    return item.model_dump()

@app.get("/item/{item_id}")
def get_item(item_id: int = Path(..., ge=1)):
    item = _items.get(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item.model_dump()

@app.get("/item")
def list_items(offset: int = Query(0, ge=0), limit: int = Query(10, gt=0), min_price: Optional[float] = Query(None, ge=0), max_price: Optional[float] = Query(None, ge=0), show_deleted: bool = Query(False)):
    items = list(_items.values())
    if not show_deleted:
        items = [i for i in items if not i.deleted]
    if min_price is not None:
        items = [i for i in items if i.price >= min_price]
    if max_price is not None:
        items = [i for i in items if i.price <= max_price]
    items = items[offset : offset + limit]
    return [i.model_dump() for i in items]

@app.put("/item/{item_id}")
def put_item(item_id: int = Path(..., ge=1), payload: ItemPut = ...):
    existing = _items.get(item_id)
    if existing is None or existing.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    existing.name = payload.name
    existing.price = float(payload.price)
    _items[item_id] = existing
    return existing.model_dump()

@app.patch("/item/{item_id}")
def patch_item(item_id: int = Path(..., ge=1), payload: ItemPatch = ...):
    existing = _items.get(item_id)
    if existing is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    if existing.deleted:
        return JSONResponse(status_code=HTTPStatus.NOT_MODIFIED, content=None)
    updated = existing.model_copy(deep=True)
    if payload.name is not None:
        updated.name = payload.name
    if payload.price is not None:
        updated.price = float(payload.price)
    _items[item_id] = updated
    return updated.model_dump()

@app.delete("/item/{item_id}")
def delete_item(item_id: int = Path(..., ge=1)):
    existing = _items.get(item_id)
    if existing is None:
        return {"status": "ok"}
    if not existing.deleted:
        existing.deleted = True
        _items[item_id] = existing
    return {"status": "ok"}

@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response):
    new_id = next(_cart_id_counter)
    _carts[new_id] = {}
    response.headers["location"] = f"/cart/{new_id}"
    return {"id": new_id}

@app.get("/cart/{cart_id}")
def get_cart(cart_id: int = Path(..., ge=1)):
    view = _build_cart_view(cart_id)
    return view.model_dump()

@app.get("/cart")
def list_carts(offset: int = Query(0, ge=0), limit: int = Query(10, gt=0), min_price: Optional[float] = Query(None, ge=0), max_price: Optional[float] = Query(None, ge=0), min_quantity: Optional[int] = Query(None, ge=0), max_quantity: Optional[int] = Query(None, ge=0)):
    views = [_build_cart_view(cid) for cid in _carts.keys()]
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
    views = views[offset : offset + limit]
    return [v.model_dump() for v in views]

@app.post("/cart/{cart_id}/add/{item_id}")
def cart_add_item(cart_id: int = Path(..., ge=1), item_id: int = Path(..., ge=1)):
    if cart_id not in _carts:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    item = _items.get(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    cart = _carts[cart_id]
    cart[item_id] = cart.get(item_id, 0) + 1
    _carts[cart_id] = cart
    return _build_cart_view(cart_id).model_dump()

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