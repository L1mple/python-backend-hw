import random
import string
import time
from typing import Dict, List, Optional

from database import engine, get_db
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from models import Base
from models import Cart as DBCart
from models import CartItem as DBCartItem
from models import Item as DBItem
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Shop API")

# Инициализация метрик Prometheus
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"]
)

ITEMS_COUNT = Gauge("shop_items_total", "Total number of items")
CARTS_COUNT = Gauge("shop_carts_total", "Total number of carts")


@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    method = request.method
    endpoint = request.url.path

    if endpoint == "/metrics":
        return await call_next(request)

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(process_time)
    REQUEST_COUNT.labels(
        method=method, endpoint=endpoint, status_code=response.status_code
    ).inc()

    return response


metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# Модели данных
class Item(BaseModel):
    id: int
    name: str
    price: float = Field(gt=0)
    deleted: bool = False

    class Config:
        from_attributes = True


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int = Field(ge=1)
    available: bool

    class Config:
        from_attributes = True


class Cart(BaseModel):
    id: int
    items: List[CartItem] = []
    price: float = Field(ge=0)

    class Config:
        from_attributes = True


class ConnectionManager:
    """Управляет WebSocket соединениями для разных комнат чата"""

    def __init__(self):
        self.active_connections: Dict[str, List[tuple[WebSocket, str]]] = {}

    def generate_username(self) -> str:
        """Генерирует случайное имя пользователя"""
        adjectives = [
            "Fast",
            "Brave",
            "Smart",
            "Cool",
            "Swift",
            "Bold",
            "Bright",
            "Quick",
        ]
        nouns = ["Tiger", "Eagle", "Wolf", "Lion", "Hawk", "Bear", "Fox", "Dragon"]
        number = "".join(random.choices(string.digits, k=3))
        return f"{random.choice(adjectives)}{random.choice(nouns)}{number}"

    async def connect(self, websocket: WebSocket, chat_name: str) -> str:
        """Подключает пользователя к комнате и возвращает его username"""
        await websocket.accept()
        username = self.generate_username()

        if chat_name not in self.active_connections:
            self.active_connections[chat_name] = []

        self.active_connections[chat_name].append((websocket, username))
        return username

    def disconnect(self, websocket: WebSocket, chat_name: str):
        """Отключает пользователя от комнаты"""
        if chat_name in self.active_connections:
            self.active_connections[chat_name] = [
                (ws, user)
                for ws, user in self.active_connections[chat_name]
                if ws != websocket
            ]
            if not self.active_connections[chat_name]:
                del self.active_connections[chat_name]

    async def broadcast(self, message: str, chat_name: str, sender_username: str):
        """Отправляет сообщение всем пользователям в комнате"""
        if chat_name not in self.active_connections:
            return

        formatted_message = f"{sender_username} :: {message}"

        to_remove = []

        for websocket, username in self.active_connections[chat_name]:
            try:
                await websocket.send_text(formatted_message)
            except Exception:
                to_remove.append(websocket)

        for ws in to_remove:
            self.disconnect(ws, chat_name)


manager = ConnectionManager()


@app.websocket("/chat/{chat_name}")
async def websocket_chat_endpoint(websocket: WebSocket, chat_name: str):
    """WebSocket endpoint для чата с поддержкой комнат"""
    username = await manager.connect(websocket, chat_name)

    try:
        while True:
            message = await websocket.receive_text()

            await manager.broadcast(message, chat_name, username)

    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_name)


def calculate_cart_price(db: Session, cart: DBCart) -> float:
    total = 0.0
    for cart_item in cart.cart_items:
        item = cart_item.item
        if not item.deleted:
            total += item.price * cart_item.quantity
    return total


@app.post("/cart", status_code=status.HTTP_201_CREATED)
async def create_cart(response: Response, db: Session = Depends(get_db)):
    db_cart = DBCart()
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)

    response.headers["location"] = f"/cart/{db_cart.id}"
    return {"id": db_cart.id}


@app.get("/cart/{cart_id}")
async def get_cart(cart_id: int, db: Session = Depends(get_db)):
    db_cart = db.query(DBCart).filter(DBCart.id == cart_id).first()
    if not db_cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    items = []
    for cart_item in db_cart.cart_items:
        items.append(
            CartItem(
                id=cart_item.item.id,
                name=cart_item.item.name,
                quantity=cart_item.quantity,
                available=not cart_item.item.deleted,
            )
        )

    cart = Cart(id=db_cart.id, items=items, price=calculate_cart_price(db, db_cart))

    return cart


@app.get("/cart")
async def get_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None,
    db: Session = Depends(get_db),
):
    # Валидация параметров
    if offset < 0:
        raise HTTPException(status_code=422, detail="Offset must be non-negative")
    if limit <= 0:
        raise HTTPException(status_code=422, detail="Limit must be positive")
    if min_price is not None and min_price < 0:
        raise HTTPException(status_code=422, detail="Min price must be non-negative")
    if max_price is not None and max_price < 0:
        raise HTTPException(status_code=422, detail="Max price must be non-negative")
    if min_quantity is not None and min_quantity < 0:
        raise HTTPException(status_code=422, detail="Min quantity must be non-negative")
    if max_quantity is not None and max_quantity < 0:
        raise HTTPException(status_code=422, detail="Max quantity must be non-negative")

    query = db.query(DBCart)
    carts = query.offset(offset).limit(limit).all()

    filtered_carts = []
    for db_cart in carts:
        items = []
        for cart_item in db_cart.cart_items:
            items.append(
                CartItem(
                    id=cart_item.item.id,
                    name=cart_item.item.name,
                    quantity=cart_item.quantity,
                    available=not cart_item.item.deleted,
                )
            )

        cart_model = Cart(
            id=db_cart.id, items=items, price=calculate_cart_price(db, db_cart)
        )

        # Фильтр по цене
        if min_price is not None and cart_model.price < min_price:
            continue
        if max_price is not None and cart_model.price > max_price:
            continue

        filtered_carts.append(cart_model)

    if min_quantity is not None or max_quantity is not None:
        total_quantity = sum(
            item.quantity for cart in filtered_carts for item in cart.items
        )

        if min_quantity is not None and total_quantity < min_quantity:
            return []
        if max_quantity is not None and total_quantity > max_quantity:
            return []

    return filtered_carts


@app.post("/cart/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    # Проверяем существование корзины
    db_cart = db.query(DBCart).filter(DBCart.id == cart_id).first()
    if not db_cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Проверяем существование товара
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    if db_item.deleted:
        raise HTTPException(status_code=400, detail="Item is deleted")

    # Проверяем, есть ли товар уже в корзине
    db_cart_item = (
        db.query(DBCartItem)
        .filter(DBCartItem.cart_id == cart_id, DBCartItem.item_id == item_id)
        .first()
    )

    if db_cart_item:
        db_cart_item.quantity += 1
        db.commit()
        db.refresh(db_cart_item)
        return {"message": "Item quantity increased"}
    else:
        # Добавляем новый товар
        new_cart_item = DBCartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(new_cart_item)
        db.commit()
        db.refresh(new_cart_item)
        return {"message": "Item added to cart"}


class ItemCreate(BaseModel):
    name: str
    price: float = Field(gt=0)


class ItemPut(BaseModel):
    """Модель для PUT - все поля обязательны"""

    name: str
    price: float = Field(gt=0)


class ItemPatch(BaseModel):
    """Модель для PATCH - все поля опциональны, extra поля запрещены"""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    price: Optional[float] = Field(gt=0, default=None)


@app.post("/item", status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = DBItem(name=item.name, price=item.price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    ITEMS_COUNT.inc()

    return Item.model_validate(db_item)


@app.get("/item/{item_id}")
async def get_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    if db_item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")

    return Item.model_validate(db_item)


@app.get("/item")
async def get_items(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    show_deleted: bool = False,
    db: Session = Depends(get_db),
):
    # Валидация параметров
    if offset < 0:
        raise HTTPException(status_code=422, detail="Offset must be non-negative")
    if limit <= 0:
        raise HTTPException(status_code=422, detail="Limit must be positive")
    if min_price is not None and min_price < 0:
        raise HTTPException(status_code=422, detail="Min price must be non-negative")
    if max_price is not None and max_price < 0:
        raise HTTPException(status_code=422, detail="Max price must be non-negative")

    query = db.query(DBItem)

    if not show_deleted:
        query = query.filter(DBItem.deleted == False)

    if min_price is not None:
        query = query.filter(DBItem.price >= min_price)
    if max_price is not None:
        query = query.filter(DBItem.price <= max_price)

    # Пагинация
    items = query.offset(offset).limit(limit).all()

    return [Item.model_validate(item) for item in items]


@app.put("/item/{item_id}")
async def update_item(
    item_id: int, item_update: ItemPut, db: Session = Depends(get_db)
):
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    if db_item.deleted:
        raise HTTPException(status_code=400, detail="Cannot update deleted item")

    # Обновляем поля
    db_item.name = item_update.name
    db_item.price = item_update.price

    db.commit()
    db.refresh(db_item)

    return Item.model_validate(db_item)


@app.patch("/item/{item_id}")
async def partial_update_item(
    item_id: int, item_update: ItemPatch, db: Session = Depends(get_db)
):
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Для удаленных товаров возвращаем 304 NOT_MODIFIED
    if db_item.deleted:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    # Обновляем только переданные поля
    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)

    db.commit()
    db.refresh(db_item)

    return Item.model_validate(db_item)


@app.delete("/item/{item_id}")
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(DBItem).filter(DBItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    db_item.deleted = True
    db.commit()

    # Обновляем метрику
    ITEMS_COUNT.dec()

    return {"message": "Item deleted successfully"}
