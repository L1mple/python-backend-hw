from typing import Annotated
from http import HTTPStatus
import random
import string
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, Query, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, create_engine, select, func
from sqlalchemy.orm import declarative_base, Session, sessionmaker, relationship

# Database setup
DATABASE_URL = "postgresql://postgres:password@localhost:5433/shop_db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# SQLAlchemy Models
class ItemOrm(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)


class CartOrm(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)


class CartItemOrm(Base):
    __tablename__ = "cart_items"

    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    quantity = Column(Integer, nullable=False)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    pass


app = FastAPI(title="Shop API", lifespan=lifespan)


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


# Database helper functions
def get_cart_from_db(db: Session, cart_id: int) -> Cart | None:
    cart = db.query(CartOrm).filter(CartOrm.id == cart_id).first()
    if not cart:
        return None

    cart_items_orm = db.query(CartItemOrm).filter(CartItemOrm.cart_id == cart_id).all()
    cart_items = []
    total_price = 0.0

    for cart_item_orm in cart_items_orm:
        item_orm = db.query(ItemOrm).filter(ItemOrm.id == cart_item_orm.item_id).first()
        if item_orm:
            available = not item_orm.deleted
            cart_items.append(
                CartItem(
                    id=item_orm.id,
                    name=item_orm.name,
                    quantity=cart_item_orm.quantity,
                    available=available,
                )
            )
            if available:
                total_price += item_orm.price * cart_item_orm.quantity

    return Cart(id=cart_id, items=cart_items, price=total_price)


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
def create_item(item: ItemCreateRequest, db: Session = Depends(get_db)) -> Item:
    item_orm = ItemOrm(name=item.name, price=item.price, deleted=False)
    db.add(item_orm)
    db.commit()
    db.refresh(item_orm)
    return Item(id=item_orm.id, name=item_orm.name, price=item_orm.price, deleted=item_orm.deleted)


@app.get("/item/{id}")
def get_item(id: int, db: Session = Depends(get_db)) -> Item:
    item_orm = db.query(ItemOrm).filter(ItemOrm.id == id).first()
    if item_orm is None or item_orm.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return Item(id=item_orm.id, name=item_orm.name, price=item_orm.price, deleted=item_orm.deleted)


@app.get("/item")
def get_items(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    show_deleted: bool = False,
    db: Session = Depends(get_db),
) -> list[Item]:
    query = db.query(ItemOrm)

    if not show_deleted:
        query = query.filter(ItemOrm.deleted == False)

    if min_price is not None:
        query = query.filter(ItemOrm.price >= min_price)

    if max_price is not None:
        query = query.filter(ItemOrm.price <= max_price)

    items_orm = query.offset(offset).limit(limit).all()
    return [Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted) for item in items_orm]


@app.put("/item/{id}")
def update_item(id: int, item: ItemUpdateRequest, db: Session = Depends(get_db)) -> Item:
    item_orm = db.query(ItemOrm).filter(ItemOrm.id == id).first()
    if item_orm is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    item_orm.name = item.name
    item_orm.price = item.price
    db.commit()
    db.refresh(item_orm)
    return Item(id=item_orm.id, name=item_orm.name, price=item_orm.price, deleted=item_orm.deleted)


@app.patch("/item/{id}")
def patch_item(id: int, item: ItemPatchRequest, db: Session = Depends(get_db)) -> Item:
    item_orm = db.query(ItemOrm).filter(ItemOrm.id == id).first()
    if item_orm is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    if item_orm.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED)

    if item.name is not None:
        item_orm.name = item.name
    if item.price is not None:
        item_orm.price = item.price

    db.commit()
    db.refresh(item_orm)
    return Item(id=item_orm.id, name=item_orm.name, price=item_orm.price, deleted=item_orm.deleted)


@app.delete("/item/{id}")
def delete_item(id: int, db: Session = Depends(get_db)) -> Response:
    item_orm = db.query(ItemOrm).filter(ItemOrm.id == id).first()
    if item_orm:
        item_orm.deleted = True
        db.commit()
    return Response(status_code=HTTPStatus.OK)


# Cart endpoints
@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response, db: Session = Depends(get_db)) -> CartCreateResponse:
    cart_orm = CartOrm()
    db.add(cart_orm)
    db.commit()
    db.refresh(cart_orm)
    response.headers["location"] = f"/cart/{cart_orm.id}"
    return CartCreateResponse(id=cart_orm.id)


@app.get("/cart/{id}")
def get_cart(id: int, db: Session = Depends(get_db)) -> Cart:
    cart = get_cart_from_db(db, id)
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
    db: Session = Depends(get_db),
) -> list[Cart]:
    all_cart_ids = db.query(CartOrm.id).all()
    filtered = []

    for (cart_id,) in all_cart_ids:
        cart = get_cart_from_db(db, cart_id)
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


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)) -> Cart:
    # Check if cart exists
    cart_orm = db.query(CartOrm).filter(CartOrm.id == cart_id).first()
    if cart_orm is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    # Check if item exists
    item_orm = db.query(ItemOrm).filter(ItemOrm.id == item_id).first()
    if item_orm is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    # Check if item already in cart
    cart_item_orm = db.query(CartItemOrm).filter(
        CartItemOrm.cart_id == cart_id,
        CartItemOrm.item_id == item_id
    ).first()

    if cart_item_orm:
        cart_item_orm.quantity += 1
    else:
        cart_item_orm = CartItemOrm(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(cart_item_orm)

    db.commit()

    cart = get_cart_from_db(db, cart_id)
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
