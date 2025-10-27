from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status, Response, Query
from pydantic import BaseModel, Field, field_validator
from typing import Annotated, Any
import random
import string
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session
from shop_api.database import init_db, get_db, DBItem, DBCart, DBCartItem

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()


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
    with get_db() as db:
        db_item = DBItem(name=item.name, price=item.price, deleted=False)
        db.add(db_item)
        db.flush()
        return Item(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)


@app.get("/item/{id}", response_model=Item)
def get_item(id: int):
    with get_db() as db:
        db_item = db.query(DBItem).filter(DBItem.id == id).first()
        if not db_item or db_item.deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return Item(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)


@app.get("/item", response_model=list[Item])
def get_items(
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(gt=0)] = 10,
        min_price: Annotated[float | None, Query(ge=0)] = None,
        max_price: Annotated[float | None, Query(ge=0)] = None,
        show_deleted: bool = False
):
    with get_db() as db:
        query = db.query(DBItem)

        if not show_deleted:
            query = query.filter(DBItem.deleted == False)

        if min_price is not None:
            query = query.filter(DBItem.price >= min_price)
        if max_price is not None:
            query = query.filter(DBItem.price <= max_price)

        db_items = query.offset(offset).limit(limit).all()
        return [Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted) for item in db_items]


@app.put("/item/{id}", response_model=Item)
def update_item(id: int, item: ItemUpdate):
    with get_db() as db:
        db_item = db.query(DBItem).filter(DBItem.id == id).first()
        if not db_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        db_item.name = item.name
        db_item.price = item.price
        db.flush()

        return Item(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)


@app.patch("/item/{id}", response_model=Item)
def patch_item(id: int, item: ItemPatch):
    with get_db() as db:
        db_item = db.query(DBItem).filter(DBItem.id == id).first()
        if not db_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        # Cannot patch deleted items
        if db_item.deleted:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED)

        # Update only provided fields
        if item.name is not None:
            db_item.name = item.name
        if item.price is not None:
            db_item.price = item.price

        db.flush()
        return Item(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)


@app.delete("/item/{id}")
def delete_item(id: int):
    with get_db() as db:
        db_item = db.query(DBItem).filter(DBItem.id == id).first()
        if not db_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        db_item.deleted = True
        db.flush()
        return Response(status_code=status.HTTP_200_OK)


# ============ Cart Endpoints ============

@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart(response: Response):
    with get_db() as db:
        db_cart = DBCart()
        db.add(db_cart)
        db.flush()

        response.headers["location"] = f"/cart/{db_cart.id}"
        return {"id": db_cart.id}


@app.get("/cart/{id}", response_model=Cart)
def get_cart(id: int):
    with get_db() as db:
        db_cart = db.query(DBCart).filter(DBCart.id == id).first()
        if not db_cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        cart_items_db = db.query(DBCartItem).filter(DBCartItem.cart_id == id).all()
        cart_items = []
        total_price = 0.0

        for cart_item in cart_items_db:
            db_item = db.query(DBItem).filter(DBItem.id == cart_item.item_id).first()
            if db_item:
                cart_items.append(CartItem(
                    id=db_item.id,
                    name=db_item.name,
                    quantity=cart_item.quantity,
                    available=not db_item.deleted
                ))
                total_price += db_item.price * cart_item.quantity

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
    with get_db() as db:
        db_carts = db.query(DBCart).all()
        filtered_carts = []

        for db_cart in db_carts:
            cart = get_cart(db_cart.id)

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
    with get_db() as db:
        db_cart = db.query(DBCart).filter(DBCart.id == cart_id).first()
        if not db_cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
        if not db_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        # Check if item already in cart
        cart_item = db.query(DBCartItem).filter(
            DBCartItem.cart_id == cart_id,
            DBCartItem.item_id == item_id
        ).first()

        if cart_item:
            cart_item.quantity += 1
        else:
            cart_item = DBCartItem(cart_id=cart_id, item_id=item_id, quantity=1)
            db.add(cart_item)

        db.flush()
        return Response(status_code=status.HTTP_200_OK)
