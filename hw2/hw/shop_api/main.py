from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from uuid import uuid4
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="Shop API")

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


def _get_item_or_404(item_id: int) -> Dict[str, Any]:
    item = _items.get(item_id)
    if item is None or item.get("deleted", False):
        raise HTTPException(status_code=404)
    return item


def _cart_price(cart: Dict[str, Any]) -> float:
    price = 0.0
    for it in cart["items"]:
        item = _items.get(it["id"])
        if item and not item.get("deleted", False):
            price += float(item["price"]) * int(it["quantity"])
    return price


def _cart_total_quantity(cart: Dict[str, Any]) -> int:
    return sum(int(it["quantity"]) for it in cart["items"])


# Cart endpoints
@app.post("/cart")
def create_cart(response: Response) -> Dict[str, int]:
    global _cart_id_seq
    cart_id = _cart_id_seq
    _cart_id_seq += 1
    _carts[cart_id] = {"id": cart_id, "items": []}
    response.headers["location"] = f"/cart/{cart_id}"
    response.status_code = 201
    CARTS_CREATED.inc()
    return {"id": cart_id}


@app.get("/cart/{cart_id}")
def get_cart(cart_id: int) -> Dict[str, Any]:
    cart = _carts.get(cart_id)
    if not cart:
        raise HTTPException(status_code=404)

    items: List[Dict[str, Any]] = []
    for it in cart["items"]:
        item = _items.get(it["id"]) or {}
        items.append(
            {
                "id": it["id"],
                "name": item.get("name"),
                "quantity": it["quantity"],
                "available": bool(item) and not item.get("deleted", False),
            }
        )

    return {"id": cart_id, "items": items, "price": _cart_price(cart)}


@app.get("/cart")
def get_cart_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
) -> List[Dict[str, Any]]:
    carts = list(_carts.values())

    def with_view(cart: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": cart["id"],
            "items": cart["items"],
            "price": _cart_price(cart),
            "_quantity": _cart_total_quantity(cart),
        }

    cart_views = [with_view(c) for c in carts]

    if min_price is not None:
        cart_views = [c for c in cart_views if c["price"] >= min_price]
    if max_price is not None:
        cart_views = [c for c in cart_views if c["price"] <= max_price]
    if min_quantity is not None:
        cart_views = [c for c in cart_views if c["_quantity"] >= min_quantity]
    if max_quantity is not None:
        cart_views = [c for c in cart_views if c["_quantity"] <= max_quantity]

    cart_views = cart_views[offset : offset + limit]

    # Build response
    result: List[Dict[str, Any]] = []
    for c in cart_views:
        cart = _carts[c["id"]]
        result.append(
            {
                "id": c["id"],
                "items": [
                    {
                        "id": it["id"],
                        "name": _items.get(it["id"], {}).get("name"),
                        "quantity": it["quantity"],
                        "available": (_items.get(it["id"]) is not None)
                        and not _items.get(it["id"], {}).get("deleted", False),
                    }
                    for it in cart["items"]
                ],
                "price": c["price"],
            }
        )

    return result


@app.post("/cart/{cart_id}/add/{item_id}")
def add_to_cart(cart_id: int, item_id: int) -> Dict[str, Any]:
    cart = _carts.get(cart_id)
    if not cart:
        raise HTTPException(status_code=404)

    item = _items.get(item_id)
    if item is None or item.get("deleted", False):
        raise HTTPException(status_code=404)

    for it in cart["items"]:
        if it["id"] == item_id:
            it["quantity"] += 1
            break
    else:
        cart["items"].append({"id": item_id, "quantity": 1})

    return {"id": cart_id}


# Item endpoints
@app.post("/item")
def create_item(item: ItemCreate, response: Response) -> Dict[str, Any]:
    global _item_id_seq
    item_id = _item_id_seq
    _item_id_seq += 1
    data = {"id": item_id, "name": item.name, "price": float(item.price), "deleted": False}
    _items[item_id] = data
    response.status_code = 201
    ITEMS_CREATED.inc()
    return data


@app.get("/item/{item_id}")
def get_item(item_id: int) -> Dict[str, Any]:
    item = _items.get(item_id)
    if item is None or item.get("deleted", False):
        raise HTTPException(status_code=404)
    return item


@app.get("/item")
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
) -> List[Dict[str, Any]]:
    items = list(_items.values())
    if not show_deleted:
        items = [it for it in items if not it.get("deleted", False)]

    if min_price is not None:
        items = [it for it in items if float(it["price"]) >= min_price]
    if max_price is not None:
        items = [it for it in items if float(it["price"]) <= max_price]

    return items[offset : offset + limit]


@app.put("/item/{item_id}")
def put_item(item_id: int, body: ItemPut) -> Dict[str, Any]:
    item = _items.get(item_id)
    if item is None or item.get("deleted", False):
        raise HTTPException(status_code=404)

    item.update({"name": body.name, "price": float(body.price)})
    return item


@app.patch("/item/{item_id}")
def patch_item(item_id: int, body: ItemPatch) -> Dict[str, Any]:
    item = _items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404)

    if item.get("deleted", False):
        return Response(status_code=304)

    updates: Dict[str, Any] = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.price is not None:
        updates["price"] = float(body.price)

    if updates:
        item.update(updates)

    return item


@app.delete("/item/{item_id}")
def delete_item(item_id: int) -> Dict[str, Any]:
    item = _items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404)

    item["deleted"] = True
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
