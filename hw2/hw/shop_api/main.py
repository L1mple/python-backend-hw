from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Response,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from typing import Optional, Dict, List
from prometheus_fastapi_instrumentator import Instrumentator
import random

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

# Хранение данных в оперативной памяти (было сказано, что так можно без БД)
items_db: dict[int, dict] = {}
carts_db: dict[int, dict] = {}
item_id_seq = 1
cart_id_seq = 1


# -------------------- ITEM --------------------


@app.post("/item", status_code=status.HTTP_201_CREATED)
def create_item(item: dict, response: Response):
    """
    Создает новый товар. Проверяем валидность name и price.
    Добавляем в базу и возвращаем с Location заголовком.
    """
    global item_id_seq

    if (
        "name" not in item
        or not isinstance(item["name"], str)
        or not item["name"].strip()
    ):
        raise HTTPException(status_code=422)

    if (
        "price" not in item
        or not isinstance(item["price"], (int, float))
        or item["price"] < 0
    ):
        raise HTTPException(status_code=422)

    item_data = {
        "id": item_id_seq,
        "name": item["name"],
        "price": float(item["price"]),
        "deleted": False,
    }
    items_db[item_id_seq] = item_data
    response.headers["Location"] = f"/item/{item_id_seq}"
    item_id_seq += 1

    return item_data


@app.get("/item/{item_id}")
def get_item(item_id: int):
    """Возвращаем товар по ID. 404 если нет или удален"""
    item = items_db.get(item_id)

    if not item or item["deleted"]:
        raise HTTPException(status_code=404)

    return item


@app.get("/item")
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False),
):
    """Список товаров с фильтром по цене и пагинацией"""
    items = list(items_db.values())

    if min_price is not None:
        items = [i for i in items if i["price"] >= min_price]

    if max_price is not None:
        items = [i for i in items if i["price"] <= max_price]

    if not show_deleted:
        items = [i for i in items if not i["deleted"]]

    return items[offset : offset + limit]


@app.put("/item/{item_id}")
def replace_item(item_id: int, item: dict):
    """Полная замена товара по ID"""
    if item_id not in items_db or items_db[item_id]["deleted"]:
        raise HTTPException(status_code=404)

    if (
        "name" not in item
        or not isinstance(item["name"], str)
        or not item["name"].strip()
    ):
        raise HTTPException(status_code=422)

    if (
        "price" not in item
        or not isinstance(item["price"], (int, float))
        or item["price"] < 0
    ):
        raise HTTPException(status_code=422)

    items_db[item_id]["name"] = item["name"]
    items_db[item_id]["price"] = float(item["price"])

    return items_db[item_id]


@app.patch("/item/{item_id}")
def patch_item(item_id: int, item: dict, response: Response):
    """Частичное обновление товара. Можно менять только name и price"""
    if item_id not in items_db:
        raise HTTPException(status_code=404)

    item_data = items_db[item_id]
    if item_data["deleted"]:
        response.status_code = status.HTTP_304_NOT_MODIFIED
        return Response(status_code=304)

    if not item:
        return item_data

    allowed_fields = {"name", "price"}
    extra_fields = set(item.keys()) - allowed_fields
    if extra_fields:
        raise HTTPException(status_code=422)

    if "name" in item:
        if not isinstance(item["name"], str) or not item["name"].strip():
            raise HTTPException(status_code=422)
        item_data["name"] = item["name"]

    if "price" in item:
        if not isinstance(item["price"], (int, float)) or item["price"] < 0:
            raise HTTPException(status_code=422)
        item_data["price"] = float(item["price"])

    return item_data


@app.delete("/item/{item_id}")
def delete_item(item_id: int):
    """Помечаем товар как удалённый"""
    if item_id not in items_db:
        raise HTTPException(status_code=404)

    items_db[item_id]["deleted"] = True

    return {"id": item_id}


# -------------------- CART --------------------


@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart(response: Response):
    """Создаём новую пустую корзину"""
    global cart_id_seq

    cart_data = {"id": cart_id_seq, "items": [], "price": 0.0}
    carts_db[cart_id_seq] = cart_data
    response.headers["Location"] = f"/cart/{cart_id_seq}"
    cart_id_seq += 1

    return cart_data


@app.get("/cart/{cart_id}")
def get_cart(cart_id: int):
    """Возвращаем корзину по ID"""
    cart = carts_db.get(cart_id)

    if not cart:
        raise HTTPException(status_code=404)

    return cart


def count_total_quantity(cart):
    """Считаем общее количество товаров в корзине"""
    return sum(item["quantity"] for item in cart["items"])


@app.get("/cart")
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    """Список корзин с фильтром по цене и количеству товаров"""
    carts = list(carts_db.values())
    if min_price is not None:
        carts = [c for c in carts if c["price"] >= min_price]

    if max_price is not None:
        carts = [c for c in carts if c["price"] <= max_price]

    if min_quantity is not None:
        carts = [c for c in carts if count_total_quantity(c) >= min_quantity]

    if max_quantity is not None:
        carts = [c for c in carts if count_total_quantity(c) <= max_quantity]

    return carts[offset : offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int):
    """Добавляем товар в корзину. Если уже есть — увеличиваем quantity"""
    cart = carts_db.get(cart_id)

    if not cart:
        raise HTTPException(status_code=404)

    item = items_db.get(item_id)

    if not item or item["deleted"]:
        raise HTTPException(status_code=404)

    for c_item in cart["items"]:
        if c_item["id"] == item_id:
            c_item["quantity"] += 1
            break
    else:
        cart["items"].append(
            {
                "id": item_id,
                "name": item["name"],
                "quantity": 1,
                "available": not item["deleted"],
            }
        )

    cart["price"] = sum(
        c["quantity"] * items_db[c["id"]]["price"] for c in cart["items"]
    )

    return cart


# ---------------- WebSocket чат ----------------


class ConnectionManager:
    """Менеджер WebSocket соединений по комнатам"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, chat_name: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(chat_name, []).append(websocket)

    def disconnect(self, chat_name: str, websocket: WebSocket):
        if chat_name in self.active_connections:
            self.active_connections[chat_name].remove(websocket)
            if not self.active_connections[chat_name]:
                del self.active_connections[chat_name]

    async def broadcast(self, chat_name: str, message: str):
        """Отправляем сообщение всем в комнате"""
        for connection in self.active_connections.get(chat_name, []):
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/chat/{chat_name}")
async def chat_endpoint(websocket: WebSocket, chat_name: str):
    """WebSocket endpoint чата. Каждому клиенту даётся случайное имя."""
    username = f"user{random.randint(1000, 9999)}"

    await manager.connect(chat_name, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(chat_name, f"{username} :: {data}")
    except WebSocketDisconnect:
        manager.disconnect(chat_name, websocket)
