from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from shop_api.models import (CartItem, CartResponse, ItemCreate, ItemPatch,
                             ItemResponse, ItemUpdate)

app = FastAPI(title="Shop API")

# Хранение данных в памяти: словари для быстрого поиска по ID
carts: Dict[int, Dict[str, Any]] = (
    {}
)  # {cart_id: {"id": int, "items": [{"id": int, "quantity": int}]}}
items: Dict[int, Dict[str, Any]] = (
    {}
)  # {item_id: {"id": int, "name": str, "price": float, "deleted": bool}}
cart_id_counter: int = 0  # Счётчик для уникальных ID корзин
item_id_counter: int = 0  # Счётчик для уникальных ID товаров


# Вспомогательные функции
def get_next_cart_id() -> int:
    """Генерация уникального ID для корзины"""
    global cart_id_counter
    cart_id_counter += 1
    return cart_id_counter


def get_next_item_id() -> int:
    """Генерация уникального ID для товара"""
    global item_id_counter
    item_id_counter += 1
    return item_id_counter


def calculate_cart_price(cart: Dict[str, Any]) -> float:
    """
    Расчёт общей цены корзины:
    Сумма (price * quantity) только для доступных товаров (не удалённых)
    """
    price = 0.0
    for cart_item in cart.get("items", []):
        item_id = cart_item["id"]
        if item_id in items and not items[item_id]["deleted"]:
            price += items[item_id]["price"] * cart_item["quantity"]
    return price


# Эндпоинты для корзин (Cart)
@app.post("/cart", status_code=HTTPStatus.CREATED, response_model=Dict[str, int])
async def create_cart() -> JSONResponse:
    """Создание новой пустой корзины, возвращает ID"""
    cart_id = get_next_cart_id()
    carts[cart_id] = {"id": cart_id, "items": []}
    return JSONResponse(
        content={"id": cart_id},
        status_code=HTTPStatus.CREATED,
        headers={"location": f"/cart/{cart_id}"},
    )


@app.get("/cart/{id}", response_model=CartResponse)
async def get_cart_by_id(id: int) -> Dict[str, Any]:
    """Получение корзины по ID"""
    if id not in carts:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Корзина не найдена"
        )

    cart = carts[id]
    cart_items = []
    for cart_item in cart["items"]:
        item_id = cart_item["id"]
        if item_id in items:
            cart_items.append(
                {
                    "id": item_id,
                    "name": items[item_id]["name"],
                    "quantity": cart_item["quantity"],
                    "available": not items[item_id]["deleted"],
                }
            )

    return {"id": cart["id"], "items": cart_items, "price": calculate_cart_price(cart)}


@app.get("/cart", response_model=List[CartResponse])
async def list_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Список корзин с фильтрами и пагинацией.
    Валидация: offset >= 0, limit > 0, цены/кол-ва >= 0
    """
    if offset < 0 or limit <= 0:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="Неверный offset или limit",
        )
    if min_price is not None and min_price < 0:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail="Неверный min_price"
        )
    if max_price is not None and max_price < 0:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail="Неверный max_price"
        )
    if min_quantity is not None and min_quantity < 0:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail="Неверный min_quantity"
        )
    if max_quantity is not None and max_quantity < 0:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail="Неверный max_quantity"
        )

    result = []
    for cart_id in sorted(carts.keys()):
        cart_response = await get_cart_by_id(cart_id)
        total_quantity = sum(item["quantity"] for item in cart_response["items"])
        cart_price = cart_response["price"]

        if min_price is not None and cart_price < min_price:
            continue
        if max_price is not None and cart_price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        result.append(cart_response)

    return result[offset : offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int) -> None:
    """Добавление товара в корзину: инкремент, если есть; добавление, если нет"""
    if cart_id not in carts:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Корзина не найдена"
        )
    if item_id not in items:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Товар не найден")

    cart = carts[cart_id]
    for cart_item in cart["items"]:
        if cart_item["id"] == item_id:
            cart_item["quantity"] += 1
            return
    cart["items"].append({"id": item_id, "quantity": 1})


# Эндпоинты для товаров (Item)
@app.post("/item", response_model=ItemResponse, status_code=HTTPStatus.CREATED)
async def create_item(item: ItemCreate) -> Dict[str, Any]:
    """Создание нового товара"""
    item_id = get_next_item_id()
    new_item = {"id": item_id, "name": item.name, "price": item.price, "deleted": False}
    items[item_id] = new_item
    return new_item


@app.get("/item/{id}", response_model=ItemResponse)
async def get_item_by_id(id: int) -> Dict[str, Any]:
    """Получение товара по ID (404, если удалён)"""
    if id not in items or items[id]["deleted"]:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Товар не найден")
    return items[id]


@app.get("/item", response_model=List[ItemResponse])
async def list_items(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    show_deleted: bool = False,
) -> List[Dict[str, Any]]:
    """
    Список товаров с фильтрами и пагинацией.
    По умолчанию не показывает удалённые.
    """
    if offset < 0 or limit <= 0:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="Неверный offset или limit",
        )
    if min_price is not None and min_price < 0:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail="Неверный min_price"
        )
    if max_price is not None and max_price < 0:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail="Неверный max_price"
        )

    result = []
    for item_id in sorted(items.keys()):
        item = items[item_id]
        if not show_deleted and item["deleted"]:
            continue
        if min_price is not None and item["price"] < min_price:
            continue
        if max_price is not None and item["price"] > max_price:
            continue
        result.append(item)

    return result[offset : offset + limit]


@app.put("/item/{id}", response_model=ItemResponse)
async def update_item(id: int, item: ItemUpdate) -> Dict[str, Any]:
    """Полная замена товара (304, если удалён)"""
    if id not in items:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Товар не найден")
    if items[id]["deleted"]:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED, detail="Товар удалён")

    updated_item = {
        "id": id,
        "name": item.name,
        "price": item.price,
        "deleted": items[id]["deleted"],
    }
    items[id] = updated_item
    return updated_item


@app.patch("/item/{id}", response_model=ItemResponse)
async def patch_item(id: int, patch_data: ItemPatch) -> Dict[str, Any]:
    """
    Частичное обновление (не трогает deleted).
    422 на попытку изменить deleted или лишние поля.
    """
    if id not in items:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Товар не найден")
    if items[id]["deleted"]:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED, detail="Товар удалён")

    updated_item = items[id].copy()
    if patch_data.name is not None:
        updated_item["name"] = patch_data.name
    if patch_data.price is not None:
        updated_item["price"] = patch_data.price

    items[id] = updated_item
    return updated_item


@app.delete("/item/{id}", status_code=HTTPStatus.OK)
async def delete_item(id: int) -> None:
    """Soft-delete: помечает как удалённый (идемпотентно)"""
    if id not in items:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Товар не найден")
    items[id]["deleted"] = True


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
        username = f"User_{uuid4().hex[:4]}"  # случайное имя типа User_a1b2
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
