from typing import Annotated
from http import HTTPStatus
import random
import string

from fastapi import FastAPI, HTTPException, Response, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI(title="Shop API")


# Models
class ItemCreateRequest(BaseModel):
    name: str
    price: float = Field(ge=0)


class ItemUpdateRequest(BaseModel):
    name: str
    price: float = Field(ge=0)


class ItemPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    price: float | None = Field(default=None, ge=0)


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


class CartCreateResponse(BaseModel):
    id: int


# Storage
class Storage:
    def __init__(self):
        self.items: dict[int, Item] = {}
        self.carts: dict[int, dict] = {}
        self.item_id_counter = 0
        self.cart_id_counter = 0

    def create_item(self, name: str, price: float) -> Item:
        self.item_id_counter += 1
        item = Item(id=self.item_id_counter, name=name, price=price, deleted=False)
        self.items[item.id] = item
        return item

    def get_item(self, item_id: int) -> Item | None:
        return self.items.get(item_id)

    def get_items(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        show_deleted: bool = False,
    ) -> list[Item]:
        filtered = []
        for item in self.items.values():
            if not show_deleted and item.deleted:
                continue
            if min_price is not None and item.price < min_price:
                continue
            if max_price is not None and item.price > max_price:
                continue
            filtered.append(item)

        return filtered[offset:offset + limit]

    def update_item(self, item_id: int, name: str, price: float) -> Item | None:
        if item_id not in self.items:
            return None
        self.items[item_id].name = name
        self.items[item_id].price = price
        return self.items[item_id]

    def patch_item(self, item_id: int, name: str | None = None, price: float | None = None) -> Item | None:
        if item_id not in self.items:
            return None
        item = self.items[item_id]
        if item.deleted:
            return None
        if name is not None:
            item.name = name
        if price is not None:
            item.price = price
        return item

    def delete_item(self, item_id: int) -> bool:
        if item_id in self.items:
            self.items[item_id].deleted = True
            return True
        return False

    def create_cart(self) -> int:
        self.cart_id_counter += 1
        cart_id = self.cart_id_counter
        self.carts[cart_id] = {}
        return cart_id

    def get_cart(self, cart_id: int) -> Cart | None:
        if cart_id not in self.carts:
            return None

        cart_items = []
        total_price = 0.0

        for item_id, quantity in self.carts[cart_id].items():
            item = self.items.get(item_id)
            if item:
                available = not item.deleted
                cart_items.append(
                    CartItem(
                        id=item.id,
                        name=item.name,
                        quantity=quantity,
                        available=available,
                    )
                )
                if available:
                    total_price += item.price * quantity

        return Cart(id=cart_id, items=cart_items, price=total_price)

    def get_carts(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        min_quantity: int | None = None,
        max_quantity: int | None = None,
    ) -> list[Cart]:
        filtered = []

        for cart_id in self.carts.keys():
            cart = self.get_cart(cart_id)
            if cart is None:
                continue

            if min_price is not None and cart.price < min_price:
                continue
            if max_price is not None and cart.price > max_price:
                continue

            total_quantity = sum(item.quantity for item in cart.items)
            if min_quantity is not None and total_quantity < min_quantity:
                continue
            if max_quantity is not None and total_quantity > max_quantity:
                continue

            filtered.append(cart)

        return filtered[offset:offset + limit]

    def add_item_to_cart(self, cart_id: int, item_id: int) -> bool:
        if cart_id not in self.carts:
            return False
        if item_id not in self.items:
            return False

        if item_id in self.carts[cart_id]:
            self.carts[cart_id][item_id] += 1
        else:
            self.carts[cart_id][item_id] = 1

        return True


storage = Storage()


# Chat management
class ChatManager:
    def __init__(self):
        # Dictionary: chat_name -> list of (websocket, username) tuples
        self.active_connections: dict[str, list[tuple[WebSocket, str]]] = {}

    def generate_username(self) -> str:
        """Generate a random username"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    async def connect(self, websocket: WebSocket, chat_name: str) -> str:
        """Connect a new user to a chat room"""
        await websocket.accept()
        username = self.generate_username()

        if chat_name not in self.active_connections:
            self.active_connections[chat_name] = []

        self.active_connections[chat_name].append((websocket, username))
        return username

    def disconnect(self, websocket: WebSocket, chat_name: str):
        """Disconnect a user from a chat room"""
        if chat_name in self.active_connections:
            self.active_connections[chat_name] = [
                (ws, user) for ws, user in self.active_connections[chat_name]
                if ws != websocket
            ]
            # Clean up empty chat rooms
            if not self.active_connections[chat_name]:
                del self.active_connections[chat_name]

    async def broadcast(self, message: str, chat_name: str, sender_username: str):
        """Broadcast a message to all users in a chat room"""
        if chat_name not in self.active_connections:
            return

        formatted_message = f"{sender_username} :: {message}"

        # Send to all connections in this chat
        for websocket, username in self.active_connections[chat_name]:
            try:
                await websocket.send_text(formatted_message)
            except:
                # If sending fails, we'll handle it in the disconnect
                pass


chat_manager = ChatManager()


# Item endpoints
@app.post("/item", status_code=HTTPStatus.CREATED)
def create_item(item: ItemCreateRequest) -> Item:
    return storage.create_item(item.name, item.price)


@app.get("/item/{id}")
def get_item(id: int) -> Item:
    item = storage.get_item(id)
    if item is None or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return item


@app.get("/item")
def get_items(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    show_deleted: bool = False,
) -> list[Item]:
    return storage.get_items(offset, limit, min_price, max_price, show_deleted)


@app.put("/item/{id}")
def update_item(id: int, item: ItemUpdateRequest) -> Item:
    updated = storage.update_item(id, item.name, item.price)
    if updated is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return updated


@app.patch("/item/{id}")
def patch_item(id: int, item: ItemPatchRequest) -> Item:
    patched = storage.patch_item(id, item.name, item.price)
    if patched is None:
        stored_item = storage.get_item(id)
        if stored_item and stored_item.deleted:
            raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED)
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return patched


@app.delete("/item/{id}")
def delete_item(id: int) -> Response:
    storage.delete_item(id)
    return Response(status_code=HTTPStatus.OK)


# Cart endpoints
@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response) -> CartCreateResponse:
    cart_id = storage.create_cart()
    response.headers["location"] = f"/cart/{cart_id}"
    return CartCreateResponse(id=cart_id)


@app.get("/cart/{id}")
def get_cart(id: int) -> Cart:
    cart = storage.get_cart(id)
    if cart is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return cart


@app.get("/cart")
def get_carts(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    min_quantity: Annotated[int | None, Query(ge=0)] = None,
    max_quantity: Annotated[int | None, Query(ge=0)] = None,
) -> list[Cart]:
    return storage.get_carts(offset, limit, min_price, max_price, min_quantity, max_quantity)


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int) -> Cart:
    success = storage.add_item_to_cart(cart_id, item_id)
    if not success:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    cart = storage.get_cart(cart_id)
    if cart is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    return cart


# WebSocket chat endpoint
@app.websocket("/chat/{chat_name}")
async def websocket_chat(websocket: WebSocket, chat_name: str):
    username = await chat_manager.connect(websocket, chat_name)
    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()
            # Broadcast to all users in the chat
            await chat_manager.broadcast(message, chat_name, username)
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket, chat_name)
