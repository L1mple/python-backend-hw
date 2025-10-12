from http import HTTPStatus
from fastapi import FastAPI, HTTPException, Response, Query
from pydantic import BaseModel, Field, ConfigDict
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_client import Counter, Histogram, Gauge
import time

app = FastAPI(title="Shop API")

# Инициализация Prometheus инструментатора
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Кастомные метрики
items_counter = Counter('shop_items_total', 'Total number of items created', ['operation'])
carts_counter = Counter('shop_carts_total', 'Total number of carts created', ['operation'])
request_duration = Histogram('shop_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
active_items = Gauge('shop_active_items', 'Number of active items in the system')
active_carts = Gauge('shop_active_carts', 'Number of active carts in the system')

class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(ge=0)

class Item(ItemIn):
    id: int
    deleted: bool = False

class CartCreated(BaseModel):
    id: int

class CartItemOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartOut(BaseModel):
    id: int
    items: list[CartItemOut]
    price: float

_carts: dict[int, dict[int, int]] = {}
_next_cart_id: int = 1
_items: dict[int, Item] = {}
_next_item_id: int = 1

@app.post("/item", response_model=Item, status_code=201)
def create_item(payload: ItemIn, response: Response) -> Item:
    start_time = time.time()
    
    global _next_item_id
    item = Item(
        id = _next_item_id,
        name = payload.name,
        price = payload.price,
        deleted = False
    )
    _items[item.id] = item
    _next_item_id += 1
    
    # Обновляем метрики
    items_counter.labels(operation='created').inc()
    active_items.set(len([i for i in _items.values() if not i.deleted]))
    request_duration.labels(method='POST', endpoint='/item').observe(time.time() - start_time)

    response.headers["Location"] = f"/item/{item.id}"
    return item

@app.get("/item/{id}", response_model=Item)
def get_item(id: int) -> Item:
    item = _items.get(id)
    if item is None or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.post("/cart", response_model=CartCreated, status_code=201)
def create_cart(response: Response) -> CartCreated:
    """Создает пустую коризну и возврашает ее id"""
    start_time = time.time()
    
    global _next_cart_id
    cart_id = _next_cart_id
    _carts[cart_id] = {}
    _next_cart_id += 1
    
    # Обновляем метрики
    carts_counter.labels(operation='created').inc()
    active_carts.set(len(_carts))
    request_duration.labels(method='POST', endpoint='/cart').observe(time.time() - start_time)

    response.headers["Location"] = f"/cart/{cart_id}"
    return CartCreated(id=cart_id)

def _build_cart_out(cart_id: int) -> CartOut:
    cart = _carts.get(cart_id)
    items_out: list[CartItemOut] = []
    total_price = 0.0

    for item_id, quantity in cart.items():
        item = _items.get(item_id)
        if item is None or item.deleted:
            continue
        available = not item.deleted
        items_out.append(CartItemOut(
            id=item_id,
            name=item.name, 
            quantity=quantity, 
            available=available
        ))

        total_price += item.price * quantity
    return CartOut(
        id=cart_id,
        items=items_out,
        price=total_price
    )

@app.get("/cart/{id}", response_model=CartOut)
def get_cart(id: int) -> CartOut:
    """
    Возвращает корзину:
    - items: список {id, name, quantity, available}
    - price: сумма price * quantity для всех товаров (0.0 для пустой корзины)
    """
    cart = _carts.get(id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    items_out: list[CartItemOut] = []
    total_price = 0.0
    # cart — это dict[item_id -> quantity]
    for item_id, quantity in cart.items():
        item = _items.get(item_id)
        if item is None or item.deleted:
            continue

        available = not item.deleted
        items_out.append(CartItemOut(
            id=item_id,
            name=item.name, 
            quantity=quantity, 
            available=available
        ))
        total_price += item.price * quantity
    return CartOut(
        id=id,
        items=items_out,
        price=total_price
    )

@app.post("/cart/{cart_id}/add/{item_id}", response_model=CartOut)
def add_to_cart(cart_id: int, item_id: int) -> CartOut:
    """
    Добавляет товар в корзину:
    - если товар уже есть, то увеличивается его количество
    - если товар не найден, то возвращается ошибка 404
    """
    cart = _carts.get(cart_id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    item = _items.get(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    cart[item_id] = int(cart.get(item_id, 0)) + 1
    return _build_cart_out(cart_id)

@app.get("/item", response_model=list[Item])
def list_items(
    show_deleted: bool = False,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, gt=0),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
) -> list[Item]:
    """
    Список товаров с фильтрами и пагинацией.
    - По умолчанию скрываем удалённые.
    - Фильтры по цене: min_price / max_price.
    - Пагинация: offset / limit.
    """
    items = list(_items.values())
    if not show_deleted:
        items = [i for i in items if not i.deleted]
    
    if min_price is not None:
        items = [it for it in items if float(it.price) >= float(min_price)]
    if max_price is not None:
        items = [it for it in items if float(it.price) <= float(max_price)]
    #фиксируем порядок
    items.sort(key=lambda x: x.id)
    start = int(offset)
    end = start + int(limit)
    return items[start:end]

@app.delete("/item/{id}", response_model=Item)
def delete_item(id: int) -> Item:
    """
    Удаляет товар:
    - товар помечается как удаленный
    """
    start_time = time.time()
    
    item = _items.get(id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    #идемптентность
    if not item.deleted:
        item.deleted = True
        # Обновляем метрики только если товар действительно удалили
        items_counter.labels(operation='deleted').inc()
        active_items.set(len([i for i in _items.values() if not i.deleted]))
    
    request_duration.labels(method='DELETE', endpoint='/item').observe(time.time() - start_time)
    return item

@app.put("/item/{id}", response_model=Item)
def put_item(id: int, payload: ItemIn) -> Item:
    """
    Заменяет товар по `id`
    """
    item = _items.get(id)
    if item is None or item.deleted:
        raise HTTPException(status_code = 404,detail="Item not found")
    item.name = payload.name
    item.price = payload.price
    return item

class ItemPatch(BaseModel):
    # Оба поля опциональные — это «частичное» обновление
    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, ge=0)
    # Запрещаем лишние поля в payload → иначе 422
    model_config = ConfigDict(extra="forbid")

@app.patch("/item/{item_id}",response_model=Item)
def patch_item(item_id:int,payload:ItemPatch):
    item = _items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Нельзя патчить удалённый товар — 304 Not Modified
    if item.deleted:
        return Response(status_code=HTTPStatus.NOT_MODIFIED)
    
    # Пустой патч {} допустим: просто ничего не меняем и возвращаем 200
    if payload.name is not None:
        item.name = payload.name
    if payload.price is not None:
        item.price = payload.price

    return item

@app.get("/cart", response_model=list[CartOut])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, gt=0),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    min_quantity: int | None = Query(None, ge=0),
    max_quantity: int | None = Query(None, ge=0),
) -> list[CartOut]:
    # получаем все корзины в едином формате
    cart_ids = sorted(_carts.keys())
    carts: list[CartOut] = [_build_cart_out(cid) for cid in cart_ids]

    # фильтры по цене корзины
    if min_price is not None:
        carts = [c for c in carts if c.price >= float(min_price)]
    if max_price is not None:
        carts = [c for c in carts if c.price <= float(max_price)]

    # фильтры по суммарному количеству товаров в корзине
    def cart_qty(c: CartOut) -> int:
        return sum(i.quantity for i in c.items)

    if min_quantity is not None:
        carts = [c for c in carts if cart_qty(c) >= int(min_quantity)]
    if max_quantity is not None:
        carts = [c for c in carts if cart_qty(c) <= int(max_quantity)]

    # пагинация
    start = int(offset)
    end = start + int(limit)
    return carts[start:end]