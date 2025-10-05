from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status, Response, Query
from pydantic import BaseModel, Field, field_validator
from typing import Annotated, Any
import random
import string
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)


# ============ Data Models ============

class ItemCreate(BaseModel):
    name: str
    price: float = Field(ge=0)


class ItemUpdate(BaseModel):
    name: str
    price: float = Field(ge=0)


class ItemPatch(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = None
    price: float | None = Field(default=None, ge=0)

    @classmethod
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('price must be non-negative')
        return v


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
    items: list[CartItem]
    price: float


# ============ In-Memory Storage ============

items_db: dict[int, Item] = {}
carts_db: dict[int, dict[int, int]] = {}  # cart_id -> {item_id -> quantity}
item_counter = 0
cart_counter = 0

# ============ WebSocket Chat ============

chat_rooms: dict[str, list[WebSocket]] = {}
client_names: dict[WebSocket, str] = {}
chat_history: dict[str, list[str]] = {}  # chat_name -> list of messages


def generate_username() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


@app.websocket("/chat/{chat_name}")
async def chat_endpoint(websocket: WebSocket, chat_name: str):
    await websocket.accept()

    # Generate random username for this client
    username = generate_username()
    client_names[websocket] = username

    # Send chat history to new client
    if chat_name in chat_history:
        for msg in chat_history[chat_name]:
            await websocket.send_text(msg)

    # Initialize chat room and history if needed
    if chat_name not in chat_rooms:
        chat_rooms[chat_name] = []
    if chat_name not in chat_history:
        chat_history[chat_name] = []

    # Add client to chat room
    chat_rooms[chat_name].append(websocket)

    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()

            # Broadcast to all clients in the same chat room
            formatted_message = f"{username} :: {message}"

            # Save to history
            chat_history[chat_name].append(formatted_message)

            # Broadcast to all connected clients
            for client in chat_rooms[chat_name]:
                await client.send_text(formatted_message)
    except WebSocketDisconnect:
        # Remove client from chat room
        chat_rooms[chat_name].remove(websocket)
        if not chat_rooms[chat_name]:
            del chat_rooms[chat_name]
        del client_names[websocket]


# ============ Item Endpoints ============

@app.post("/item", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate):
    global item_counter
    item_counter += 1
    new_item = Item(id=item_counter, name=item.name, price=item.price, deleted=False)
    items_db[item_counter] = new_item
    return new_item


@app.get("/item/{id}", response_model=Item)
def get_item(id: int):
    if id not in items_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    item = items_db[id]
    if item.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return item


@app.get("/item", response_model=list[Item])
def get_items(
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(gt=0)] = 10,
        min_price: Annotated[float | None, Query(ge=0)] = None,
        max_price: Annotated[float | None, Query(ge=0)] = None,
        show_deleted: bool = False
):
    filtered_items = []

    for item in items_db.values():
        # Filter by deleted status
        if not show_deleted and item.deleted:
            continue

        # Filter by price
        if min_price is not None and item.price < min_price:
            continue
        if max_price is not None and item.price > max_price:
            continue

        filtered_items.append(item)

    return filtered_items[offset:offset + limit]


@app.put("/item/{id}", response_model=Item)
def update_item(id: int, item: ItemUpdate):
    if id not in items_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    existing_item = items_db[id]
    existing_item.name = item.name
    existing_item.price = item.price

    return existing_item


@app.patch("/item/{id}", response_model=Item)
def patch_item(id: int, item: ItemPatch):
    if id not in items_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    existing_item = items_db[id]

    # Cannot patch deleted items
    if existing_item.deleted:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    # Update only provided fields
    if item.name is not None:
        existing_item.name = item.name
    if item.price is not None:
        existing_item.price = item.price

    return existing_item


@app.delete("/item/{id}")
def delete_item(id: int):
    if id not in items_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    items_db[id].deleted = True
    return Response(status_code=status.HTTP_200_OK)


# ============ Cart Endpoints ============

@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart(response: Response):
    global cart_counter
    cart_counter += 1
    carts_db[cart_counter] = {}

    response.headers["location"] = f"/cart/{cart_counter}"
    return {"id": cart_counter}


@app.get("/cart/{id}", response_model=Cart)
def get_cart(id: int):
    if id not in carts_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    cart_items_dict = carts_db[id]
    cart_items = []
    total_price = 0.0

    for item_id, quantity in cart_items_dict.items():
        if item_id in items_db:
            item = items_db[item_id]
            cart_items.append(CartItem(
                id=item.id,
                name=item.name,
                quantity=quantity,
                available=not item.deleted
            ))
            total_price += item.price * quantity

    return Cart(id=id, items=cart_items, price=total_price)


@app.get("/cart", response_model=list[Cart])
def get_carts(
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(gt=0)] = 10,
        min_price: Annotated[float | None, Query(ge=0)] = None,
        max_price: Annotated[float | None, Query(ge=0)] = None,
        min_quantity: Annotated[int | None, Query(ge=0)] = None,
        max_quantity: Annotated[int | None, Query(ge=0)] = None
):
    filtered_carts = []

    for cart_id in carts_db:
        cart = get_cart(cart_id)

        # Filter by price
        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue

        # Calculate total quantity
        total_quantity = sum(item.quantity for item in cart.items)

        # Filter by quantity
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        filtered_carts.append(cart)

    return filtered_carts[offset:offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if item_id not in items_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    cart = carts_db[cart_id]

    if item_id in cart:
        cart[item_id] += 1
    else:
        cart[item_id] = 1

    return Response(status_code=status.HTTP_200_OK)
