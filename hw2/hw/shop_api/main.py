from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.params import Query
from fastapi.responses import JSONResponse


app = FastAPI(title="Shop API")

items_storage: Dict[int, Dict[str, Any]] = {}
carts_storage: Dict[int, Dict[str, Any]] = {}

_next_item_id: int = 1
_next_cart_id: int = 1

def _generate_item_id() -> int:
    global _next_item_id
    item_id = _next_item_id
    _next_item_id += 1
    return item_id

def _generate_cart_id() -> int:
    global _next_cart_id
    cart_id = _next_cart_id
    _next_cart_id += 1
    return cart_id

def _get_item_or_404(item_id: int) -> Dict[str, Any]:
    item = items_storage.get(item_id)
    if item is None or item.get("deleted") is True:
        raise HTTPException(status_code=404)
    return item

def _compute_cart_price(cart: Dict[str, Any]) -> float:
    total_price = 0.0
    for entry in cart["items"]:
        item_id = entry["id"]
        quantity = entry["quantity"]
        item = items_storage.get(item_id)
        if item is None or item.get("deleted") is True:
            continue
        total_price += float(item["price"]) * int(quantity)
    return float(total_price)

def _total_quantity_in_cart(cart: Dict[str, Any]) -> int:
    return int(sum(entry["quantity"] for entry in cart["items"]))

# --------------
# Item endpoints
# --------------

@app.post("/item")
def create_item(body: Dict[str, Any]):
    if not isinstance(body, dict):
        raise HTTPException(status_code=422)

    if "name" not in body or "price" not in body:
        raise HTTPException(status_code=422)

    item_id = _generate_item_id()
    item = {
        "id": item_id,
        "name": body["name"],
        "price": float(body["price"]),
        "deleted": False,
    }
    items_storage[item_id] = item

    response = JSONResponse(status_code=201, content=item)
    return response

@app.get("/item/{item_id}")
def get_item(item_id: int):
    item = _get_item_or_404(item_id)
    return item

@app.get("/item")
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0.0),
    max_price: Optional[float] = Query(default=None, ge=0.0),
    show_deleted: bool = Query(default=False),
):
    items: List[Dict[str, Any]] = list(items_storage.values())

    if not show_deleted:
        items = [it for it in items if it.get("deleted") is False]

    if min_price is not None:
        items = [it for it in items if float(it["price"]) >= float(min_price)]
    if max_price is not None:
        items = [it for it in items if float(it["price"]) <= float(max_price)]

    items = items[offset : offset + limit]
    return items

@app.put("/item/{item_id}")
def replace_item(item_id: int, body: Dict[str, Any]):
    existing = items_storage.get(item_id)
    if existing is None:
        raise HTTPException(status_code=404)

    if not isinstance(body, dict) or "name" not in body or "price" not in body:
        raise HTTPException(status_code=422)

    existing.update({
        "name": body["name"],
        "price": float(body["price"]),
    })
    return existing

@app.patch("/item/{item_id}")
def patch_item(item_id: int, body: Dict[str, Any]):
    existing = items_storage.get(item_id)
    if existing is None:
        raise HTTPException(status_code=404)

    if existing.get("deleted") is True:
        return JSONResponse(status_code=304, content=None)

    if not isinstance(body, dict):
        raise HTTPException(status_code=422)

    allowed_keys = {"name", "price"}
    if any(key not in allowed_keys for key in body.keys()):
        raise HTTPException(status_code=422)
    if "deleted" in body:
        raise HTTPException(status_code=422)

    if "name" in body:
        existing["name"] = body["name"]
    if "price" in body:
        existing["price"] = float(body["price"])

    return existing

@app.delete("/item/{item_id}")
def delete_item(item_id: int):
    existing = items_storage.get(item_id)
    if existing is None:
        return {"status": "ok"}

    existing["deleted"] = True
    return {"status": "ok"}

# --------------
# Cart endpoints
# --------------

@app.post("/cart")
def create_cart():
    cart_id = _generate_cart_id()
    cart = {"id": cart_id, "items": []}  
    carts_storage[cart_id] = cart

    response = JSONResponse(status_code=201, content={"id": cart_id})
    response.headers["Location"] = f"/cart/{cart_id}"
    return response

@app.get("/cart/{cart_id}")
def get_cart(cart_id: int):
    cart = carts_storage.get(cart_id)
    if cart is None:
        raise HTTPException(status_code=404)

    result = {
        "id": cart["id"],
        "items": cart["items"],
        "price": _compute_cart_price(cart),
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
):
    carts: List[Dict[str, Any]] = list(carts_storage.values())

    if min_price is not None:
        carts = [c for c in carts if _compute_cart_price(c) >= float(min_price)]
    if max_price is not None:
        carts = [c for c in carts if _compute_cart_price(c) <= float(max_price)]

    if min_quantity is not None:
        carts = [c for c in carts if _total_quantity_in_cart(c) >= int(min_quantity)]
    if max_quantity is not None:
        carts = [c for c in carts if _total_quantity_in_cart(c) <= int(max_quantity)]

    carts = carts[offset : offset + limit]

    result = [
        {"id": c["id"], "items": c["items"], "price": _compute_cart_price(c)}
        for c in carts
    ]
    return result

@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int):
    cart = carts_storage.get(cart_id)
    if cart is None:
        raise HTTPException(status_code=404)

    item = items_storage.get(item_id)
    if item is None or item.get("deleted") is True:
        raise HTTPException(status_code=404)

    for entry in cart["items"]:
        if entry["id"] == item_id:
            entry["quantity"] = int(entry["quantity"]) + 1
            break
    else:
        cart["items"].append({"id": item_id, "quantity": 1})

    return {"id": cart_id}

# --------------
# WebSocket Chat 
# --------------

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
                continue
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws)

rooms: Dict[str, ChatRoom] = {}

def _get_or_create_room(chat_name: str) -> ChatRoom:
    room = rooms.get(chat_name)
    if room is None:
        room = ChatRoom()
        rooms[chat_name] = room
    return room

def _generate_username() -> str:
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
