import itertools
from http import HTTPStatus
from threading import Lock
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict

app = FastAPI(title="Shop API")


class ItemCreate(BaseModel):
    name: str
    price: float


class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class Cart(BaseModel):
    id: int
    items: List[CartItem]
    price: float


_items: Dict[int, Item] = {}
_carts: Dict[int, Dict[int, int]] = {}  # cart_id -> {item_id: quantity}
_lock = Lock()
_item_id_counter = itertools.count(1)
_cart_id_counter = itertools.count(1)


def _compute_cart(cart_id: int) -> Cart:
    if cart_id not in _carts:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Cart not found")
    items_map = _carts[cart_id]
    items_list: List[CartItem] = []
    total_price = 0.0
    for item_id, qty in items_map.items():
        item = _items.get(item_id)
        if not item:
            items_list.append(CartItem(id=item_id, name="<unknown>", quantity=qty, available=False))
            continue
        available = not item.deleted
        items_list.append(CartItem(id=item.id, name=item.name, quantity=qty, available=available))
        if available:
            total_price += item.price * qty
    return Cart(id=cart_id, items=items_list, price=total_price)


@app.post("/item", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate):
    with _lock:
        new_id = next(_item_id_counter)
        new_item = Item(id=new_id, name=item.name, price=item.price, deleted=False)
        _items[new_id] = new_item
    return new_item


@app.get("/item/{id}", response_model=Item)
def get_item(id: int):
    item = _items.get(id)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    if item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item deleted")
    return item


@app.get("/item", response_model=List[Item])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
):
    items = list(_items.values())
    if not show_deleted:
        items = [it for it in items if not it.deleted]
    if min_price is not None:
        items = [it for it in items if it.price >= min_price]
    if max_price is not None:
        items = [it for it in items if it.price <= max_price]
    items.sort(key=lambda x: x.id)
    return items[offset : offset + limit]


@app.put("/item/{id}", response_model=Item)
def replace_item(id: int, item: ItemCreate):
    existing = _items.get(id)
    if not existing:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Item not found")
    existing.name = item.name
    existing.price = item.price
    return existing


@app.patch("/item/{id}", response_model=Item)
def patch_item(id: int, item: ItemPatch):
    existing = _items.get(id)
    if not existing:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Item not found")
    if existing.deleted:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
    if item.name is not None:
        existing.name = item.name
    if item.price is not None:
        existing.price = item.price
    return existing


@app.delete("/item/{id}")
def delete_item(id: int):
    existing = _items.get(id)
    if not existing:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Item not found")
    existing.deleted = True
    return {"ok": True}


@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart(response: Response):
    with _lock:
        new_id = next(_cart_id_counter)
        _carts[new_id] = {}
    response.headers["Location"] = f"/cart/{new_id}"
    return {"id": new_id}


@app.get("/cart/{id}", response_model=Cart)
def get_cart(id: int):
    return _compute_cart(id)


@app.get("/cart", response_model=List[Cart])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),  # 👈 вот здесь
    max_price: Optional[float] = Query(None, ge=0),  # 👈 и здесь
    min_quantity: Optional[int] = Query(None, ge=0),  # 👈 и тут
    max_quantity: Optional[int] = Query(None, ge=0),  # 👈 и тут
):
    carts = []
    for cart_id in sorted(_carts.keys()):
        cart = _compute_cart(cart_id)
        # Apply filters
        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue
        total_qty = sum(ci.quantity for ci in cart.items)
        if min_quantity is not None and total_qty < min_quantity:
            continue
        if max_quantity is not None and total_qty > max_quantity:
            continue
        carts.append(cart)
    return carts[offset : offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}")
def add_to_cart(cart_id: int, item_id: int):
    if cart_id not in _carts:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Cart not found")
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    items_map = _carts[cart_id]
    items_map[item_id] = items_map.get(item_id, 0) + 1
    # Return current cart
    return _compute_cart(cart_id)


class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, List[WebSocket]] = {}
        self.names: Dict[WebSocket, str] = {}
        self._name_counter = itertools.count(1)

    async def connect(self, chat_name: str, websocket: WebSocket):
        await websocket.accept()
        self.active.setdefault(chat_name, []).append(websocket)
        # Assign random-ish username
        username = f"user{next(self._name_counter)}"
        self.names[websocket] = username
        return username

    def disconnect(self, chat_name: str, websocket: WebSocket):
        self.active.get(chat_name, []).remove(websocket)
        self.names.pop(websocket, None)

    async def broadcast(self, chat_name: str, message: str, sender: WebSocket):
        username = self.names.get(sender, "unknown")
        framed = f"{username} :: {message}"
        conns = list(self.active.get(chat_name, []))
        for conn in conns:
            if conn is sender:
                continue
            try:
                await conn.send_text(framed)
            except Exception:
                # ignore send errors
                pass


manager = ConnectionManager()


@app.websocket("/chat/{chat_name}")
async def chat_endpoint(websocket: WebSocket, chat_name: str):
    username = await manager.connect(chat_name, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(chat_name, data, websocket)
    except WebSocketDisconnect:
        manager.disconnect(chat_name, websocket)
    except Exception:
        manager.disconnect(chat_name, websocket)
        try:
            await websocket.close()
        except Exception:
            pass
