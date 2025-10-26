from .db import engine, Base, get_db  # <- импортируем БД-объекты
from . import models
from http import HTTPStatus
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response, Query, Depends
from pydantic import BaseModel, Field, ConfigDict
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_client import Counter, Histogram, Gauge
import time
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import ItemModel, CartModel, CartItemModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    # старт приложения
    Base.metadata.create_all(bind=engine)  # создаст таблицы, если их нет
    yield
    # остановка приложения (опционально: чистить ресурсы, пулы, фоновые задачи)

app = FastAPI(title="Shop API", lifespan=lifespan)

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
def create_item(payload: ItemIn, response: Response, db: Session = Depends(get_db)) -> Item:
    row = ItemModel(name=payload.name, price=payload.price, deleted=False)
    db.add(row)
    db.commit()
    db.refresh(row)
    response.headers["Location"] = f"/item/{row.id}"
    return Item(id=row.id, name=row.name, price=row.price, deleted=row.deleted)

@app.get("/item/{item_id}", response_model=Item)
def get_item(item_id: int, db: Session = Depends(get_db)) -> Item:
    row = db.get(ItemModel, item_id)
    if row is None or row.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return Item(id=row.id, name=row.name, price=row.price, deleted=row.deleted)

@app.post("/cart", response_model=CartCreated, status_code=201)
def create_cart(response: Response, db: Session = Depends(get_db)) -> CartCreated:
    row = CartModel()
    db.add(row)
    db.commit()
    db.refresh(row)
    response.headers["Location"] = f"/cart/{row.id}"
    return CartCreated(id=row.id)

def _build_cart_out_db(db: Session, cart_id: int) -> CartOut:
    # проверим, что корзина существует
    cart = db.get(CartModel, cart_id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    # достанем позиции корзины с данными товаров
    stmt = (
        select(CartItemModel.item_id, CartItemModel.quantity,
               ItemModel.name, ItemModel.price, ItemModel.deleted)
        .join(ItemModel, ItemModel.id == CartItemModel.item_id)
        .where(CartItemModel.cart_id == cart_id)
    )
    rows = db.execute(stmt).all()

    items_out: list[CartItemOut] = []
    total_price = 0.0

    for item_id, qty, name, price, deleted in rows:
        items_out.append(CartItemOut(
            id=int(item_id),
            name=name,
            quantity=int(qty),
            available=not bool(deleted),
        ))
        total_price += float(price) * int(qty)  # считаем по текущей цене

    return CartOut(id=cart_id, items=items_out, price=float(total_price))

@app.get("/cart/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int, db: Session = Depends(get_db)) -> CartOut:
    return _build_cart_out_db(db, cart_id)

@app.post("/cart/{cart_id}/add/{item_id}", response_model=CartOut)
def add_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)) -> CartOut:
    # 1) существование корзины и товара
    cart = db.get(CartModel, cart_id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    item = db.get(ItemModel, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # 2) upsert позиции корзины
    row = db.get(CartItemModel, {"cart_id": cart_id, "item_id": item_id})
    if row is None:
        row = CartItemModel(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(row)
    else:
        row.quantity = int(row.quantity) + 1
        db.add(row)

    db.commit()
    # 3) вернуть актуальную корзину
    return _build_cart_out_db(db, cart_id)

@app.get("/item", response_model=list[Item])
def list_items(
    show_deleted: bool = False,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, gt=0),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    db: Session = Depends(get_db),
) -> list[Item]:
    stmt = select(ItemModel)

    # фильтры
    if not show_deleted:
        stmt = stmt.where(ItemModel.deleted.is_(False))
    if min_price is not None:
        stmt = stmt.where(ItemModel.price >= float(min_price))
    if max_price is not None:
        stmt = stmt.where(ItemModel.price <= float(max_price))

    # порядок + пагинация
    stmt = stmt.order_by(ItemModel.id).offset(int(offset)).limit(int(limit))

    rows = db.execute(stmt).scalars().all()  # -> list[ItemModel]
    return [Item(id=r.id, name=r.name, price=r.price, deleted=r.deleted) for r in rows]

@app.delete("/item/{item_id}", response_model=Item)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> Item:
    row = db.get(ItemModel, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # идемпотентность: повторный DELETE остаётся 200
    if not row.deleted:
        row.deleted = True
        db.add(row)
        db.commit()
        db.refresh(row)

    return Item(id=row.id, name=row.name, price=row.price, deleted=row.deleted)

@app.put("/item/{item_id}", response_model=Item)
def replace_item(item_id: int, payload: ItemIn, db: Session = Depends(get_db)) -> Item:
    row = db.get(ItemModel, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")

    row.name = payload.name
    row.price = payload.price
    db.add(row)
    db.commit()
    db.refresh(row)

    return Item(id=row.id, name=row.name, price=row.price, deleted=row.deleted)

class ItemPatch(BaseModel):
    # Оба поля опциональные — это «частичное» обновление
    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, ge=0)
    # Запрещаем лишние поля в payload → иначе 422
    model_config = ConfigDict(extra="forbid")

@app.patch("/item/{item_id}", response_model=Item)
def patch_item(item_id: int, payload: ItemPatch, db: Session = Depends(get_db)):
    row = db.get(ItemModel, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # Нельзя патчить удалённый товар
    if row.deleted:
        return Response(status_code=HTTPStatus.NOT_MODIFIED)

    changed = False
    if payload.name is not None:
        row.name = payload.name
        changed = True
    if payload.price is not None:
        row.price = payload.price
        changed = True

    if changed:
        db.add(row)
        db.commit()
        db.refresh(row)

    return Item(id=row.id, name=row.name, price=row.price, deleted=row.deleted)

@app.get("/cart", response_model=list[CartOut])
def list_carts(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int  = Query(50, gt=0),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    min_quantity: int | None = Query(None, ge=0),
    max_quantity: int | None = Query(None, ge=0),
) -> list[CartOut]:
    # берём все id корзин (отсортированные, для стабильности)
    ids = [row[0] for row in db.execute(select(CartModel.id)).all()]
    carts = [_build_cart_out_db(db, cid) for cid in ids]

    # фильтры по цене
    if min_price is not None:
        carts = [c for c in carts if c.price >= float(min_price)]
    if max_price is not None:
        carts = [c for c in carts if c.price <= float(max_price)]

    # фильтры по суммарному количеству
    def total_qty(c: CartOut) -> int:
        return sum(i.quantity for i in c.items)

    if min_quantity is not None:
        carts = [c for c in carts if total_qty(c) >= int(min_quantity)]
    if max_quantity is not None:
        carts = [c for c in carts if total_qty(c) <= int(max_quantity)]

    # пагинация
    start = int(offset)
    end = start + int(limit)
    return carts[start:end]