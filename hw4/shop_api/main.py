import random
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shop_api.models import (Base, Cart, CartItem, CartResponse, Item, ItemCreate, ItemPatch,
                             ItemResponse, ItemUpdate, CartItemResponse)

# Основное приложение FastAPI
app = FastAPI(title="Shop API")

# Интеграция с Prometheus для мониторинга метрик
Instrumentator().instrument(app).expose(app)

# настройки подключения к postgresql
DATABASE_URL = "postgresql+asyncpg://user:password@postgres:5432/shop_db"
engine = create_async_engine(DATABASE_URL, echo=True)  # echo=True для логирования SQL-запросов
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Dependency для получения асинхронной сессии БД
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

# Событие запуска: создание таблиц в БД, если они не существуют
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Вспомогательная функция для имитации случайной ошибки (для тестирования)
def maybe_raise_random_error():
    if random.random() < 0.1:  # 10% шанс ошибки
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Random error occurred")

@app.get("/test-error")
async def test_error():
    """Эндпоинт для имитации случайной ошибки"""
    maybe_raise_random_error()
    return {"message": "No error this time"}


@app.get("/")
async def root():
    return {"message": "Welcome to Shop API! Go to /docs for documentation."}

# --- Эндпоинты для корзин (Cart) ---

@app.post("/cart", status_code=HTTPStatus.CREATED, response_model=Dict[str, int])
async def create_cart(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Создание новой пустой корзины, возвращает ID"""
    cart = Cart()
    db.add(cart)
    await db.commit()
    await db.refresh(cart)
    return JSONResponse(
        content={"id": cart.id},
        status_code=HTTPStatus.CREATED,
        headers={"location": f"/cart/{cart.id}"},
    )


@app.get("/cart/{id}", response_model=CartResponse)
async def get_cart_by_id(id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Получение корзины по ID с расчётом цены и доступности товаров"""
    try:
        cart = await db.get(Cart, id)
        if not cart:
            raise NoResultFound
        items = []
        price = 0.0
        for cart_item in cart.items:
            if not cart_item.item.deleted:
                items.append(
                    CartItemResponse(
                        id=cart_item.item_id,
                        name=cart_item.item.name,
                        quantity=cart_item.quantity,
                        available=True,
                    )
                )
                price += cart_item.item.price * cart_item.quantity
            else:
                items.append(
                    CartItemResponse(
                        id=cart_item.item_id,
                        name=cart_item.item.name,
                        quantity=cart_item.quantity,
                        available=False,
                    )
                )
        return CartResponse(id=cart.id, items=items, price=price)
    except NoResultFound:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Корзина не найдена")

@app.get("/cart", response_model=List[CartResponse])
async def list_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Список корзин с фильтрами и пагинацией.
    Фильтрация по цене и количеству товаров в корзине.
    """
    # Валидация параметров
    if offset < 0 or limit <= 0:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Неверный offset или limit")
    if min_price is not None and min_price < 0:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Неверный min_price")
    if max_price is not None and max_price < 0:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Неверный max_price")
    if min_quantity is not None and min_quantity < 0:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Неверный min_quantity")
    if max_quantity is not None and max_quantity < 0:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Неверный max_quantity")

    # Получение всех корзин и фильтрация в памяти (для простоты)
    stmt = select(Cart)
    result = await db.execute(stmt)
    carts_list = result.scalars().all()
    filtered = []
    for cart in carts_list:
        cart_response = await get_cart_by_id(cart.id, db)  # Используем функцию для получения полной корзины
        total_quantity = sum(item.quantity for item in cart_response.items)
        if (min_price is not None and cart_response.price < min_price) or \
           (max_price is not None and cart_response.price > max_price) or \
           (min_quantity is not None and total_quantity < min_quantity) or \
           (max_quantity is not None and total_quantity > max_quantity):
            continue
        filtered.append(cart_response)
    return filtered[offset:offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Добавление товара в корзину: инкремент, если есть; добавление, если нет"""
    cart = await db.get(Cart, cart_id)
    if not cart:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Корзина не найдена")
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Товар не найден")

    # проверка наличия товара в корзине
    existing = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart_id, CartItem.item_id == item_id)
    )
    cart_item = existing.scalar_one_or_none()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(cart_item)
    await db.commit()

# --- Эндпоинты для товаров (Item) ---

@app.post("/item", response_model=ItemResponse, status_code=HTTPStatus.CREATED)
async def create_item(item_data: ItemCreate, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Создание нового товара"""
    item = Item(name=item_data.name, price=item_data.price)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ItemResponse(id=item.id, name=item.name, price=item.price, deleted=item.deleted)

@app.get("/item/{id}", response_model=ItemResponse)
async def get_item_by_id(id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """получение товара по id (404, если удалён)"""
    item = await db.get(Item, id)
    if not item or item.deleted:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Товар не найден")
    return ItemResponse(id=item.id, name=item.name, price=item.price, deleted=item.deleted)

@app.get("/item", response_model=List[ItemResponse])
async def list_items(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    show_deleted: bool = False,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Список товаров с фильтрами и пагинацией.
    По умолчанию не показывает удалённые.
    """
    # Валидация параметров
    if offset < 0 or limit <= 0:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Неверный offset или limit")
    if min_price is not None and min_price < 0:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Неверный min_price")
    if max_price is not None and max_price < 0:
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY, "Неверный max_price")

    # Построение SQL-запроса с фильтрами
    stmt = select(Item)
    if not show_deleted:
        stmt = stmt.where(Item.deleted == False)
    if min_price is not None:
        stmt = stmt.where(Item.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Item.price <= max_price)
    stmt = stmt.offset(offset).limit(limit).order_by(Item.id)
    result = await db.execute(stmt)
    items_list = result.scalars().all()
    return [ItemResponse(id=i.id, name=i.name, price=i.price, deleted=i.deleted) for i in items_list]

@app.put("/item/{id}", response_model=ItemResponse)
async def update_item(id: int, item_data: ItemUpdate, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Полная замена товара (304, если удалён)"""
    item = await db.get(Item, id)
    if not item:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Товар не найден")
    if item.deleted:
        raise HTTPException(HTTPStatus.NOT_MODIFIED, "Товар удалён")
    item.name = item_data.name
    item.price = item_data.price
    await db.commit()
    await db.refresh(item)
    return ItemResponse(id=item.id, name=item.name, price=item.price, deleted=item.deleted)

@app.patch("/item/{id}", response_model=ItemResponse)
async def patch_item(id: int, patch_data: ItemPatch, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Частичное обновление (не трогает deleted).
    422 на попытку изменить deleted или лишние поля (обеспечивается Pydantic).
    """
    item = await db.get(Item, id)
    if not item:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Товар не найден")
    if item.deleted:
        raise HTTPException(HTTPStatus.NOT_MODIFIED, "Товар удалён")
    if patch_data.name is not None:
        item.name = patch_data.name
    if patch_data.price is not None:
        item.price = patch_data.price
    await db.commit()
    await db.refresh(item)
    return ItemResponse(id=item.id, name=item.name, price=item.price, deleted=item.deleted)

@app.delete("/item/{id}", status_code=HTTPStatus.OK)
async def delete_item(id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Soft-delete: помечает как удалённый (идемпотентно)"""
    item = await db.get(Item, id)
    if not item:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Товар не найден")
    item.deleted = True
    await db.commit()


# WebSocket чат
@dataclass(slots=True)
class Broadcaster:
    """Класс для broadcast в одной комнате"""

    subscribers: list[WebSocket] = field(init=False, default_factory=list)
    usernames: Dict[WebSocket, str] = field(
        init=False, default_factory=dict
    )  # {ws: username}

    async def subscribe(self, ws: WebSocket) -> str:
        """Подписка клиента, присвоение имени"""
        await ws.accept()
        self.subscribers.append(ws)
        username = f"User_{uuid4().hex[:5]}"  # случайное имя типа User_a1b2
        self.usernames[ws] = username
        return username

    async def unsubscribe(self, ws: WebSocket) -> str:
        """Отписка клиента"""
        if ws in self.subscribers:
            self.subscribers.remove(ws)
            username = self.usernames.pop(ws, "unknown")
            return username
        return "unknown"

    async def publish(
        self, message: str, exclude_ws: Optional[WebSocket] = None
    ) -> None:
        """Broadcast сообщения в комнату, исключая exclude_ws"""
        dead_ws = []
        for ws in self.subscribers:
            if ws == exclude_ws:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                dead_ws.append(ws)
        # Удаляем мертвые соединения
        for dead in dead_ws:
            await self.unsubscribe(dead)


# Хранение комнат для чата (stateful, в памяти)
chat_rooms: Dict[str, Broadcaster] = {}  # {chat_name: Broadcaster}

# WebSocket эндпоинт для чата
@app.websocket("/chat/{chat_name}")
async def ws_chat(ws: WebSocket, chat_name: str):
    """Подключение к чату в комнате {chat_name}"""
    # Получаем или создаём broadcaster для комнаты
    if chat_name not in chat_rooms:
        chat_rooms[chat_name] = Broadcaster()
    broadcaster = chat_rooms[chat_name]

    # Подписка и отправка приветствия (всем, кроме самого)
    username = await broadcaster.subscribe(ws)
    await broadcaster.publish(f"{username} :: joined the chat", exclude_ws=ws)

    try:
        while True:
            # Получаем сообщение от клиента
            message = await ws.receive_text()
            message = message.strip()
            if not message:  # Пропускаем пустые сообщения
                continue
            # Форматируем и broadcast (исключая отправителя)
            formatted_message = f"{username} :: {message}"
            await broadcaster.publish(formatted_message, exclude_ws=ws)
    except WebSocketDisconnect:
        # Отписка и уведомление (всем)
        username = await broadcaster.unsubscribe(ws)
        await broadcaster.publish(f"{username} :: left the chat")
    except Exception as e:
        # Обработка других ошибок (для стабильности)
        await broadcaster.unsubscribe(ws)
        await broadcaster.publish(f"{username} :: disconnected unexpectedly")
    finally:
        # Если комната пустая — удаляем
        if not broadcaster.subscribers:
            del chat_rooms[chat_name]
