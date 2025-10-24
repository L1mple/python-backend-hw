from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ConfigDict


app = FastAPI(title="Shop API")


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False


class ItemCreate(BaseModel):
    name: str
    price: float = Field(ge=0)


class ItemReplace(BaseModel):
    name: str
    price: float = Field(ge=0)


class ItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)


class CartItem(BaseModel):
    item_id: int
    quantity: int = 0


class Cart(BaseModel):
    id: int
    items: Dict[int, CartItem] = Field(default_factory=dict)


items_store: Dict[int, Item] = {}
item_id_counter: int = 1

carts_store: Dict[int, Cart] = {}
cart_id_counter: int = 1


def get_next_item_id() -> int:
    global item_id_counter
    next_id = item_id_counter
    item_id_counter += 1
    return next_id


def get_next_cart_id() -> int:
    global cart_id_counter
    next_id = cart_id_counter
    cart_id_counter += 1
    return next_id


def compute_cart_price(cart: Cart) -> float:
    total: float = 0.0
    for cart_item in cart.items.values():
        item = items_store.get(cart_item.item_id)
        if item is None:
            continue
        total += item.price * cart_item.quantity
    return total


def compute_cart_quantity(cart: Cart) -> int:
    return sum(ci.quantity for ci in cart.items.values())


def cart_to_response(cart: Cart) -> dict:
    response_items: List[dict] = []
    for cart_item in cart.items.values():
        item = items_store.get(cart_item.item_id)
        if item is None:
            continue
        response_items.append(
            {
                "id": item.id,
                "name": item.name,
                "quantity": cart_item.quantity,
                "available": not item.deleted,
            }
        )
    return {
        "id": cart.id,
        "items": response_items,
        "price": compute_cart_price(cart),
    }


@app.post("/item", status_code=201)
def create_item(item_in: ItemCreate):
    item_id = get_next_item_id()
    item = Item(id=item_id, name=item_in.name, price=item_in.price, deleted=False)
    items_store[item_id] = item
    return item.model_dump()


@app.get("/item/{item_id}")
def get_item(item_id: int):
    item = items_store.get(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=404)
    return item.model_dump()


@app.get("/item")
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    show_deleted: bool = Query(False),
):
    data: List[Item] = list(items_store.values())

    if not show_deleted:
        data = [i for i in data if not i.deleted]

    if min_price is not None:
        data = [i for i in data if i.price >= min_price]

    if max_price is not None:
        data = [i for i in data if i.price <= max_price]

    sliced = data[offset : offset + limit]
    return [i.model_dump() for i in sliced]


@app.put("/item/{item_id}")
def replace_item(item_id: int, item_in: ItemReplace):
    item = items_store.get(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=404)
    item.name = item_in.name
    item.price = item_in.price
    items_store[item_id] = item
    return item.model_dump()


@app.patch("/item/{item_id}")
def patch_item(item_id: int, patch: ItemPatch):
    item = items_store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404)
    if item.deleted:
        return Response(status_code=304)

    updated = item.model_copy()
    if patch.name is not None:
        updated.name = patch.name
    if patch.price is not None:
        updated.price = patch.price
    items_store[item_id] = updated
    return updated.model_dump()


@app.delete("/item/{item_id}")
def delete_item(item_id: int):
    item = items_store.get(item_id)
    if item is not None:
        item.deleted = True
        items_store[item_id] = item
    return {"status": "ok"}


@app.post("/cart", status_code=201)
def create_cart(response: Response):
    cart_id = get_next_cart_id()
    carts_store[cart_id] = Cart(id=cart_id, items={})
    response.headers["Location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@app.get("/cart/{cart_id}")
def get_cart(cart_id: int):
    cart = carts_store.get(cart_id)
    if cart is None:
        raise HTTPException(status_code=404)
    return cart_to_response(cart)


@app.get("/cart")
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    min_quantity: Optional[int] = Query(default=None, ge=0),
    max_quantity: Optional[int] = Query(default=None, ge=0),
):
    carts: List[Cart] = list(carts_store.values())

    def within_price(cart: Cart) -> bool:
        price = compute_cart_price(cart)
        if min_price is not None and price < min_price:
            return False
        if max_price is not None and price > max_price:
            return False
        return True

    def within_quantity(cart: Cart) -> bool:
        qty = compute_cart_quantity(cart)
        if min_quantity is not None and qty < min_quantity:
            return False
        if max_quantity is not None and qty > max_quantity:
            return False
        return True

    filtered = [c for c in carts if within_price(c) and within_quantity(c)]
    sliced = filtered[offset : offset + limit]
    return [cart_to_response(c) for c in sliced]


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int):
    cart = carts_store.get(cart_id)
    if cart is None:
        raise HTTPException(status_code=404)
    item = items_store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404)
    existing = cart.items.get(item_id)
    if existing is None:
        cart.items[item_id] = CartItem(item_id=item_id, quantity=1)
    else:
        existing.quantity += 1
        cart.items[item_id] = existing
    carts_store[cart_id] = cart
    return cart_to_response(cart)


class ChatRoomManager:
    def __init__(self) -> None:
        self.rooms: Dict[str, set[WebSocket]] = {}
        self.usernames: Dict[WebSocket, str] = {}

    async def connect(self, room: str, websocket: WebSocket) -> str:
        await websocket.accept()
        username = f"user-{uuid4().hex[:8]}"
        self.rooms.setdefault(room, set()).add(websocket)
        self.usernames[websocket] = username
        return username

    def disconnect(self, room: str, websocket: WebSocket) -> None:
        connections = self.rooms.get(room)
        if connections is not None and websocket in connections:
            connections.remove(websocket)
            if not connections:
                self.rooms.pop(room, None)
        self.usernames.pop(websocket, None)

    async def broadcast(self, room: str, message: str, sender: Optional[WebSocket] = None) -> None:
        for ws in list(self.rooms.get(room, set())):
            if sender is not None and ws is sender:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(room, ws)

    def username_for(self, websocket: WebSocket) -> str:
        return self.usernames.get(websocket, "unknown")


chat_manager = ChatRoomManager()


@app.websocket("/chat/{chat_name}")
async def chat_websocket(websocket: WebSocket, chat_name: str):
    username = await chat_manager.connect(chat_name, websocket)
    try:
        while True:
            message = await websocket.receive_text()
            formatted = f"{username} :: {message}"
            await chat_manager.broadcast(chat_name, formatted, sender=websocket)
    except WebSocketDisconnect:
        chat_manager.disconnect(chat_name, websocket)
