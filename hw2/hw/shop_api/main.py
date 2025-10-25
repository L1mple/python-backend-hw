from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Body, status, Response, Depends

from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from .models import ItemCreate, ItemUpdate, ItemPatch, ItemOut, CartOut, CartItemOut
from .db import get_db
from .orm import Item, Cart, CartItem

# ----- WebSocket chat -----
from typing import Dict
from uuid import uuid4
from fastapi import WebSocket, WebSocketDisconnect


app = FastAPI(title="Shop API (DB-backed)")

# ---------- helpers ----------

def _dec_to_float(v: Decimal | float | int) -> float:
    return float(v) if isinstance(v, Decimal) else float(v)

def _item_to_out(i: Item) -> ItemOut:
    return ItemOut(id=i.id, name=i.name, price=_dec_to_float(i.price), deleted=i.deleted)

def _cart_to_out(db: Session, cart: Cart) -> CartOut:
    # соберём элементы корзины и цену
    # items подцеплены через relationship selectin/joined
    items_out: List[CartItemOut] = []
    total_price: float = 0.0
    for ci in cart.items:
        available = not ci.item.deleted
        items_out.append(
            CartItemOut(
                id=ci.item_id,
                name=ci.item.name,
                quantity=ci.quantity,
                available=available,
            )
        )
        if available:
            total_price += _dec_to_float(ci.item.price) * ci.quantity

    return CartOut(id=cart.id, items=items_out, price=total_price)

# ---------- Item endpoints ----------

@app.post("/item", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, response: Response, db: Session = Depends(get_db)):
    obj = Item(name=item.name, price=item.price, deleted=False)
    db.add(obj)
    db.flush()  # чтобы получить id
    response.headers["Location"] = f"/item/{obj.id}"
    db.refresh(obj)
    return _item_to_out(obj)

@app.get("/item/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(Item, item_id)
    if not obj or obj.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return _item_to_out(obj)

@app.get("/item", response_model=List[ItemOut])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
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
    rows = db.execute(stmt).scalars().all()
    return [_item_to_out(r) for r in rows]

@app.put("/item/{item_id}", response_model=ItemOut)
def update_item(item_id: int, data: ItemUpdate, db: Session = Depends(get_db)):
    obj = db.get(Item, item_id)
    if not obj or obj.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    obj.name = data.name
    obj.price = Decimal(str(data.price))
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return _item_to_out(obj)

@app.patch("/item/{item_id}", response_model=ItemOut)
def patch_item(item_id: int, data: ItemPatch = Body(...), db: Session = Depends(get_db)):
    obj = db.get(Item, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Item not found")
    if obj.deleted:
        # сохраняем поведение твоего варианта
        raise HTTPException(status_code=304, detail="Item deleted")
    incoming = data.model_dump(exclude_unset=True)
    if "deleted" in incoming:
        raise HTTPException(status_code=422, detail="Cannot patch deleted field")
    allowed = {"name", "price"}
    if not set(incoming).issubset(allowed):
        raise HTTPException(status_code=422, detail="Unexpected fields")

    if "name" in incoming:
        obj.name = incoming["name"]
    if "price" in incoming:
        obj.price = Decimal(str(incoming["price"]))
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return _item_to_out(obj)

@app.delete("/item/{item_id}", response_model=ItemOut)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    obj = db.get(Item, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Item not found")
    obj.deleted = True
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return _item_to_out(obj)

# ---------- Cart endpoints ----------

@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart(response: Response, db: Session = Depends(get_db)):
    cart = Cart()
    db.add(cart)
    db.flush()
    response.headers["Location"] = f"/cart/{cart.id}"
    return {"id": cart.id}

@app.get("/cart/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = db.get(Cart, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    # подгрузим элементы
    db.refresh(cart)
    return _cart_to_out(db, cart)

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
    # получаем корзины пачкой
    carts = db.execute(select(Cart).offset(offset).limit(limit)).scalars().all()
    outs = [_cart_to_out(db, c) for c in carts]

    # фильтры по цене/quantity в Python (для простоты)
    if min_price is not None:
        outs = [c for c in outs if c.price >= min_price]
    if max_price is not None:
        outs = [c for c in outs if c.price <= max_price]
    if min_quantity is not None:
        outs = [c for c in outs if sum(i.quantity for i in c.items) >= min_quantity]
    if max_quantity is not None:
        outs = [c for c in outs if sum(i.quantity for i in c.items) <= max_quantity]
    return outs

@app.post("/cart/{cart_id}/add/{item_id}", response_model=CartOut)
def add_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = db.get(Cart, cart_id)
    item = db.get(Item, item_id)
    if not cart or not item:
        raise HTTPException(status_code=404, detail="Cart or Item not found")

    ci = db.get(CartItem, {"cart_id": cart_id, "item_id": item_id})
    if ci:
        ci.quantity += 1
    else:
        ci = CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(ci)
    db.flush()
    db.refresh(cart)
    return _cart_to_out(db, cart)

# ---------- WebSocket chat (как было) ----------

ROOMS: Dict[str, Dict[WebSocket, str]] = {}  # room -> {websocket: username}

def _username() -> str:
    return f"user-{uuid4().hex[:6]}"

@app.websocket("/chat/{chat_name}")
async def chat_ws(websocket: WebSocket, chat_name: str):
    await websocket.accept()
    username = _username()

    room = ROOMS.setdefault(chat_name, {})
    room[websocket] = username

    try:
        for ws, user in list(room.items()):
            if ws is not websocket:
                await ws.send_text(f"* {username} joined *")

        while True:
            msg = await websocket.receive_text()
            text = f"{username} :: {msg}"
            for ws, user in list(room.items()):
                if ws is not websocket:
                    await ws.send_text(text)

    except WebSocketDisconnect:
        room.pop(websocket, None)
        for ws in list(room.keys()):
            try:
                await ws.send_text(f"* {username} left *")
            except Exception:
                pass
        if not room:
            ROOMS.pop(chat_name, None)
