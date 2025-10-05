from fastapi import FastAPI, HTTPException, Query, status, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import List, Optional, Dict

import uuid
from collections import defaultdict


app = FastAPI(title="Shop API")

# ----------------- MODELS -----------------
class Item(BaseModel):
    id: int
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)

class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, gt=0)

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int = Field(..., ge=0)
    available: bool = True

class Cart(BaseModel):
    id: int
    items: List[CartItem] = []

    @computed_field
    @property
    def price(self) -> float:
        total = 0.0
        for it in self.items:
            price = items_db.get(it.id).price if it.id in items_db else 0.0
            total += price * it.quantity
        return total

# ----------------- STORAGE -----------------
items_db: dict[int, Item] = {}
carts_db: dict[int, Cart] = {}
item_counter = 0
cart_counter = 0

# ----------------- ITEMS -----------------
@app.post("/item", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate):
    global item_counter
    item_counter += 1
    new_item = Item(id=item_counter, **item.model_dump())
    items_db[item_counter] = new_item
    return new_item

@app.get("/item/{item_id}", response_model=Item)
def get_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]

@app.get("/item", response_model=List[Item])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
):
    items = list(items_db.values())
    if min_price is not None:
        items = [i for i in items if i.price >= min_price]
    if max_price is not None:
        items = [i for i in items if i.price <= max_price]
    return items[offset : offset + limit]

@app.put("/item/{item_id}", response_model=Item)
def replace_item(item_id: int, new_item: ItemCreate):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    item = Item(id=item_id, **new_item.model_dump())
    items_db[item_id] = item
    return item

@app.patch("/item/{item_id}", response_model=Item)
def patch_item(item_id: int, upd: ItemUpdate):
    if item_id not in items_db:
        raise HTTPException(status_code=304, detail="Item not modified")
    current = items_db[item_id]
    updated = current.model_copy(update=upd.model_dump(exclude_unset=True))
    items_db[item_id] = updated
    return updated

@app.delete("/item/{item_id}", status_code=status.HTTP_200_OK)
def delete_item(item_id: int):
    items_db.pop(item_id, None)
    return Response(status_code=status.HTTP_200_OK)

# ----------------- CARTS -----------------
@app.post("/cart", response_model=Cart, status_code=status.HTTP_201_CREATED)
def create_cart(response: Response):
    global cart_counter
    cart_counter += 1
    new_cart = Cart(id=cart_counter, items=[])
    carts_db[cart_counter] = new_cart
    response.headers["Location"] = f"/cart/{cart_counter}"
    return new_cart

@app.get("/cart/{cart_id}", response_model=Cart)
def get_cart(cart_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=404, detail="Cart not found")
    return carts_db[cart_id]

@app.get("/cart", response_model=List[Cart])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    carts = list(carts_db.values())

    def matches_filters(cart: Cart) -> bool:
        total_qty = sum(i.quantity for i in cart.items)
        total_price = 0.0
        for it in cart.items:
            total_price += (items_db.get(it.id).price if it.id in items_db else 0.0) * it.quantity

        if min_price is not None and total_price < min_price:
            return False
        if max_price is not None and total_price > max_price:
            return False
        if min_quantity is not None and total_qty < min_quantity:
            return False
        if max_quantity is not None and total_qty > max_quantity:
            return False
        return True

    filtered = [c for c in carts if matches_filters(c)]
    return filtered[offset : offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart, status_code=status.HTTP_200_OK)
def add_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=404, detail="Cart not found")
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")

    cart = carts_db[cart_id]
    for it in cart.items:
        if it.id == item_id:
            it.quantity += 1
            break
    else:
        item = items_db[item_id]
        cart.items.append(CartItem(id=item_id, name=item.name, quantity=1, available=True))

    return cart

# ----------------- WEBSOCKET CHAT -----------------
rooms: Dict[str, Dict[WebSocket, str]] = defaultdict(dict)

@app.websocket("/chat/{chat_name}")
async def chat_ws(websocket: WebSocket, chat_name: str):
    await websocket.accept()
    username = f"user-{uuid.uuid4().hex[:8]}"
    rooms[chat_name][websocket] = username

    try:
        while True:
            message = await websocket.receive_text()
            formatted = f"{username} :: {message}"

            for ws, _uname in list(rooms[chat_name].items()):
                if ws is websocket:
                    continue
                try:
                    await ws.send_text(formatted)
                except Exception:
                    rooms[chat_name].pop(ws, None)

    except WebSocketDisconnect:
        pass
    finally:
        rooms[chat_name].pop(websocket, None)
        if not rooms[chat_name]:
            rooms.pop(chat_name, None)


