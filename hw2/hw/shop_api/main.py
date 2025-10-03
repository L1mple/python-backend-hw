from fastapi import FastAPI, HTTPException, Query, Body, status, Response
from typing import List, Optional

from .models import ItemCreate, ItemUpdate, ItemPatch, ItemOut, CartOut
from .storage import ITEMS, CARTS, next_item_id, next_cart_id, compute_cart

# ----- WebSocket chat -----
from typing import Dict
from uuid import uuid4
from fastapi import WebSocket, WebSocketDisconnect


app = FastAPI(title="Shop API")


# ----- Item endpoints -----
@app.post("/item", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, response: Response):
    item_id = next_item_id()
    ITEMS[item_id] = {
        "id": item_id,
        "name": item.name,
        "price": item.price,
        "deleted": False,
    }
    response.headers["Location"] = f"/item/{item_id}"
    return ITEMS[item_id]


@app.get("/item/{item_id}", response_model=ItemOut)
def get_item(item_id: int):
    item = ITEMS.get(item_id)
    if not item or item["deleted"]:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.get("/item", response_model=List[ItemOut])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
):
    items = list(ITEMS.values())
    if not show_deleted:
        items = [i for i in items if not i["deleted"]]
    if min_price is not None:
        items = [i for i in items if i["price"] >= min_price]
    if max_price is not None:
        items = [i for i in items if i["price"] <= max_price]

    return items[offset : offset + limit]


@app.put("/item/{item_id}", response_model=ItemOut)
def update_item(item_id: int, data: ItemUpdate):
    if item_id not in ITEMS or ITEMS[item_id]["deleted"]:
        raise HTTPException(status_code=404, detail="Item not found")
    ITEMS[item_id].update(data.model_dump())
    return ITEMS[item_id]


@app.patch("/item/{item_id}", response_model=ItemOut)
def patch_item(item_id: int, data: ItemPatch = Body(...)):
    item = ITEMS.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["deleted"]:
        raise HTTPException(status_code=304, detail="Item deleted")

    incoming = data.model_dump(exclude_unset=True)
    if "deleted" in incoming:
        raise HTTPException(status_code=422, detail="Cannot patch deleted field")

    allowed = {"name", "price"}
    if not set(incoming).issubset(allowed):
        raise HTTPException(status_code=422, detail="Unexpected fields")

    item.update(incoming)
    return item


@app.delete("/item/{item_id}", response_model=ItemOut)
def delete_item(item_id: int):
    item = ITEMS.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item["deleted"] = True
    return item


# ----- Cart endpoints -----
@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart(response: Response):
    cart_id = next_cart_id()
    CARTS[cart_id] = {"id": cart_id, "items": {}}
    response.headers["Location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@app.get("/cart/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int):
    cart = CARTS.get(cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return compute_cart(cart)


@app.get("/cart", response_model=List[CartOut])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    carts = [compute_cart(c) for c in CARTS.values()]

    if min_price is not None:
        carts = [c for c in carts if c["price"] >= min_price]
    if max_price is not None:
        carts = [c for c in carts if c["price"] <= max_price]

    if min_quantity is not None:
        carts = [c for c in carts if sum(i["quantity"] for i in c["items"]) >= min_quantity]
    if max_quantity is not None:
        carts = [c for c in carts if sum(i["quantity"] for i in c["items"]) <= max_quantity]

    return carts[offset : offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}", response_model=CartOut)
def add_to_cart(cart_id: int, item_id: int):
    cart = CARTS.get(cart_id)
    item = ITEMS.get(item_id)
    if not cart or not item:
        raise HTTPException(status_code=404, detail="Cart or Item not found")
    cart["items"][item_id] = cart["items"].get(item_id, 0) + 1
    return compute_cart(cart)


# ----- WebSocket chat -----

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
        # опционально: сообщим остальным, что пользователь вошёл
        for ws, user in list(room.items()):
            if ws is not websocket:
                await ws.send_text(f"* {username} joined *")

        while True:
            msg = await websocket.receive_text()
            # рассылаем всем кроме отправителя
            text = f"{username} :: {msg}"
            for ws, user in list(room.items()):
                if ws is not websocket:
                    await ws.send_text(text)

    except WebSocketDisconnect:
        # убрать из комнаты
        room.pop(websocket, None)
        # опционально: сообщить о выходе
        for ws in list(room.keys()):
            try:
                await ws.send_text(f"* {username} left *")
            except Exception:
                pass
        # если комната опустела — удалить
        if not room:
            ROOMS.pop(chat_name, None)
