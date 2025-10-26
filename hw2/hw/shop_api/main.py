from fastapi import FastAPI, Response, Query, HTTPException, Depends, status
from typing import List, Optional
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator

import psycopg2
from psycopg2.extras import RealDictCursor

# Функция для получения подключения и курсора
def get_db():
    conn = psycopg2.connect(
        dbname="shop_db",
        user="user",
        password="qwerty",
        host="localhost",
        port=5430
    )
    try:
        yield conn
    finally:
        conn.close()

def get_cursor(conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cur
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        cur.close()

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

class Item(BaseModel):
    id: int
    name: str
    price: float = Field(gt=0)
    deleted: bool = False

class ItemForCreateUpd(BaseModel):
    name: str
    price: float = Field(gt=0)

class ItemForPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    model_config = {"extra": "forbid"}

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class Cart(BaseModel):
    id: int
    items: list[CartItem]
    price: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаем подключение и курсор вручную, т.к. Depends не работает здесь
    conn = psycopg2.connect(
        dbname="shop_db",
        user="user",
        password="qwerty",
        host="localhost",
        port=5430
    )
    cur = conn.cursor()
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price FLOAT CHECK (price > 0) NOT NULL,
            deleted BOOLEAN DEFAULT FALSE NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS carts (
            id SERIAL PRIMARY KEY,
            price FLOAT NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS cart_items (
            id SERIAL PRIMARY KEY,
            cart_id INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
            item_id INTEGER NOT NULL REFERENCES items(id),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            available BOOLEAN DEFAULT TRUE NOT NULL
        );
        """)
        conn.commit()
        yield
    finally:
        cur.close()
        conn.close()

app.router.lifespan_context = lifespan

#Работа с товарами
#----------------------------------

# Создание товара
@app.post("/item", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemForCreateUpd, cur=Depends(get_cursor)):
    cur.execute(
        "INSERT INTO items (name, price, deleted) VALUES (%s, %s, FALSE) RETURNING id, name, price, deleted;",
        (item.name, item.price)
    )
    new_item = cur.fetchone()
    return new_item

# Полное обновление товара (PUT)
@app.put("/item/{id}", response_model=Item)
def put_item(id: int, item: ItemForCreateUpd, cur=Depends(get_cursor)):
    cur.execute("SELECT id FROM items WHERE id = %s AND deleted = FALSE;", (id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="Item not found")

    cur.execute(
        "UPDATE items SET name = %s, price = %s WHERE id = %s RETURNING id, name, price, deleted;",
        (item.name, item.price, id)
    )
    updated_item = cur.fetchone()
    return updated_item

# Получение списка товаров с фильтрами и пагинацией
@app.get("/item", response_model=List[Item])
def get_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
    cur=Depends(get_cursor)
):
    query = "SELECT id, name, price, deleted FROM items WHERE TRUE"
    params = []

    if not show_deleted:
        query += " AND deleted = FALSE"
    if min_price is not None:
        query += " AND price >= %s"
        params.append(min_price)
    if max_price is not None:
        query += " AND price <= %s"
        params.append(max_price)

    query += " ORDER BY id OFFSET %s LIMIT %s"
    params.extend([offset, limit])

    cur.execute(query, tuple(params))
    items = cur.fetchall()
    return items

# Получение товара по id
@app.get("/item/{id}", response_model=Item)
def get_item_id(id: int, cur=Depends(get_cursor)):
    cur.execute("SELECT id, name, price, deleted FROM items WHERE id = %s AND deleted = FALSE;", (id,))
    item = cur.fetchone()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

# Логическое удаление товара
@app.delete("/item/{id}", response_model=Item)
def delete_item(id: int, cur=Depends(get_cursor)):
    cur.execute("SELECT id FROM items WHERE id = %s AND deleted = FALSE;", (id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="Item not found")

    cur.execute(
        "UPDATE items SET deleted = TRUE WHERE id = %s RETURNING id, name, price, deleted;",
        (id,)
    )
    deleted_item = cur.fetchone()
    return deleted_item

# Частичное обновление товара (PATCH)
@app.patch("/item/{id}", response_model=Item)
def patch_item(id: int, item: ItemForPatch, cur=Depends(get_cursor)):
    cur.execute("SELECT id, name, price, deleted FROM items WHERE id = %s AND deleted = FALSE;", (id,))
    stored_item = cur.fetchone()
    if stored_item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    new_name = item.name if item.name is not None else stored_item['name']
    new_price = item.price if item.price is not None else stored_item['price']

    cur.execute(
        "UPDATE items SET name = %s, price = %s WHERE id = %s RETURNING id, name, price, deleted;",
        (new_name, new_price, id)
    )
    updated_item = cur.fetchone()
    return updated_item


#Работа с корзиной
#----------------------------------

# Создание новой корзины
@app.post("/cart", status_code=status.HTTP_201_CREATED)
def post_cart(response: Response, cur=Depends(get_cursor)):
    # Создаем пустую корзину с ценой 0
    cur.execute("INSERT INTO carts (price) VALUES (0) RETURNING id;")
    cart_id = cur.fetchone()['id']
    response.headers["location"] = f"/cart/{cart_id}"
    return {"id": cart_id}

# Получение списка корзин с фильтрами
@app.get("/cart", response_model=List[Cart])
def get_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    cur=Depends(get_cursor)
):
    # Получаем корзины с пагинацией
    cur.execute("""
        SELECT id, price FROM carts
        ORDER BY id
        OFFSET %s LIMIT %s;
    """, (offset, limit))
    carts = cur.fetchall()

    filtered_carts = []

    for cart in carts:
        cart_id = cart['id']

        # Получаем элементы корзины с данными о товарах
        cur.execute("""
            SELECT ci.item_id, ci.quantity, i.name, i.deleted, i.price
            FROM cart_items ci
            JOIN items i ON ci.item_id = i.id
            WHERE ci.cart_id = %s;
        """, (cart_id,))
        items = cur.fetchall()

        total_quantity = 0
        total_price = 0
        cart_items = []

        for item in items:
            available = not item['deleted']
            cart_items.append(CartItem(
                id=item['item_id'],
                name=item['name'],
                quantity=item['quantity'],
                available=available
            ))
            if available:
                total_price += item['price'] * item['quantity']
            total_quantity += item['quantity']

        # Фильтрация по количеству и цене
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        if min_price is not None and total_price < min_price:
            continue
        if max_price is not None and total_price > max_price:
            continue

        filtered_carts.append(Cart(
            id=cart_id,
            items=cart_items,
            price=total_price
        ))

    return filtered_carts

# Получение корзины по id
@app.get("/cart/{id}", response_model=Cart)
def get_cart_id(id: int, cur=Depends(get_cursor)):
    # Проверяем, что корзина существует
    cur.execute("SELECT id FROM carts WHERE id = %s;", (id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Получаем элементы корзины
    cur.execute("""
        SELECT ci.item_id, ci.quantity, i.name, i.deleted, i.price
        FROM cart_items ci
        JOIN items i ON ci.item_id = i.id
        WHERE ci.cart_id = %s;
    """, (id,))
    items = cur.fetchall()

    cart_items = []
    total_price = 0

    for item in items:
        available = not item['deleted']
        cart_items.append(CartItem(
            id=item['item_id'],
            name=item['name'],
            quantity=item['quantity'],
            available=available
        ))
        if available:
            total_price += item['price'] * item['quantity']

    return Cart(
        id=id,
        items=cart_items,
        price=total_price
    )

# Добавление товара в корзину
@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart)
def add_item_to_cart(cart_id: int, item_id: int, cur=Depends(get_cursor)):
    # Проверяем, что корзина существует
    cur.execute("SELECT id FROM carts WHERE id = %s;", (cart_id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Проверяем, что товар существует и не удалён
    cur.execute("SELECT id, deleted FROM items WHERE id = %s;", (item_id,))
    item = cur.fetchone()
    if item is None or item['deleted']:
        raise HTTPException(status_code=404, detail="Item not found or deleted")

    # Проверяем, есть ли уже этот товар в корзине
    cur.execute("""
        SELECT quantity FROM cart_items
        WHERE cart_id = %s AND item_id = %s;
    """, (cart_id, item_id))
    existing = cur.fetchone()

    if existing:
        # Увеличиваем количество на 1
        cur.execute("""
            UPDATE cart_items SET quantity = quantity + 1
            WHERE cart_id = %s AND item_id = %s;
        """, (cart_id, item_id))
    else:
        # Вставляем новую запись
        cur.execute("""
            INSERT INTO cart_items (cart_id, item_id, quantity, available)
            VALUES (%s, %s, 1, TRUE);
        """, (cart_id, item_id))

    # Обновляем общую цену корзины
    cur.execute("""
        SELECT SUM(i.price * ci.quantity)
        FROM cart_items ci
        JOIN items i ON ci.item_id = i.id
        WHERE ci.cart_id = %s AND i.deleted = FALSE;
    """, (cart_id,))
    total_price = cur.fetchone()[0] or 0

    cur.execute("UPDATE carts SET price = %s WHERE id = %s;", (total_price, cart_id))

    # Возвращаем обновленную корзину (используем уже готовый эндпоинт)
    return get_cart_id(cart_id, cur)
