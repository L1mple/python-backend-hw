from fastapi import (
    FastAPI, APIRouter, Query, Path, Depends, HTTPException, status, Response
)
from typing import Optional
from contextlib import asynccontextmanager
import aiosqlite

conn: aiosqlite.Connection | None = None

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS item (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  price REAL NOT NULL,
  deleted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cart (
  id INTEGER PRIMARY KEY AUTOINCREMENT
);

CREATE TABLE IF NOT EXISTS cart_item (
  cart_id INTEGER NOT NULL,
  item_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (cart_id, item_id)
);
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global conn
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    yield
    await conn.close()

app = FastAPI(title="Shop API", lifespan=lifespan)
api_router_cart = APIRouter(prefix='/cart')
api_router_item = APIRouter(prefix='/item')


async def get_conn() -> aiosqlite.Connection:
    global conn
    if conn is None:
        conn = await aiosqlite.connect(":memory:")
        conn.row_factory = aiosqlite.Row
        await conn.executescript(SCHEMA_SQL)
    return conn


@api_router_cart.post('/', status_code=status.HTTP_201_CREATED)
async def create_cart(response: Response, db: aiosqlite.Connection = Depends(get_conn)):
    cursor = await db.execute("INSERT INTO cart DEFAULT VALUES")
    await db.commit()
    cart_id = cursor.lastrowid
    response.headers["location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@api_router_cart.get('/{id}', status_code=status.HTTP_200_OK)
async def get_cart_by_id(
    id: int = Path(ge=0, description="ID корзины"),
    db: aiosqlite.Connection = Depends(get_conn)
):
    cart_exists = await db.execute("SELECT id FROM cart WHERE id = ?", (id,))
    if not await cart_exists.fetchone():

        raise HTTPException(status_code=404, detail="Cart not found")

    query = """
    SELECT 
        ci.item_id,
        ci.quantity,
        i.name,
        i.price,
        i.deleted
    FROM cart_item ci
    LEFT JOIN item i ON ci.item_id = i.id
    WHERE ci.cart_id = ?
    """
    cursor = await db.execute(query, (id,))
    rows = await cursor.fetchall()

    items = []
    total_price = 0.0

    for row in rows:
        item = {
            "id": row["item_id"],
            "name": row["name"],
            "quantity": row["quantity"],
            "available": not bool(row["deleted"])
        }
        items.append(item)
        if not row["deleted"]:
            total_price += row["price"] * row["quantity"]

    return {
        "id": id,
        "items": items,
        "price": total_price
    }


@api_router_cart.get('/', status_code=status.HTTP_200_OK)
async def get_carts_params(
    offset: int = Query(0, ge=0, description="Смещение по списку"),
    limit: int = Query(10, ge=1, le=100, description="Ограничение на количество"),
    min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена включительно"),
    max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена включительно"),
    min_quantity: Optional[int] = Query(None, ge=0, description="Минимальное число товаров включительно"),
    max_quantity: Optional[int] = Query(None, ge=0, description="Максимальное число товаров включительно"),
    db: aiosqlite.Connection = Depends(get_conn)
):
    query = """
    SELECT 
        c.id,
        COALESCE(SUM(CASE WHEN i.deleted = 0 THEN ci.quantity * i.price ELSE 0 END), 0) as total_price,
        SUM(ci.quantity) as total_quantity
    FROM cart c
    LEFT JOIN cart_item ci ON c.id = ci.cart_id
    LEFT JOIN item i ON ci.item_id = i.id
    GROUP BY c.id
    """

    conditions = []
    params = []

    if min_price is not None:
        conditions.append("total_price >= ?")
        params.append(min_price)

    if max_price is not None:
        conditions.append("total_price <= ?")
        params.append(max_price)

    if min_quantity is not None:
        conditions.append("total_quantity >= ?")
        params.append(min_quantity)

    if max_quantity is not None:
        conditions.append("total_quantity <= ?")
        params.append(max_quantity)

    if conditions:
        query += " HAVING " + " AND ".join(conditions)

    query += " ORDER BY c.id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    result = []
    for row in rows:
        cart_id = row["id"]

        items_query = """
        SELECT 
            ci.item_id,
            ci.quantity,
            i.name,
            i.price,
            i.deleted
        FROM cart_item ci
        LEFT JOIN item i ON ci.item_id = i.id
        WHERE ci.cart_id = ?
        """
        items_cursor = await db.execute(items_query, (cart_id,))
        items_rows = await items_cursor.fetchall()

        items = []
        for item_row in items_rows:
            items.append({
                "id": item_row["item_id"],
                "name": item_row["name"],
                "quantity": item_row["quantity"],
                "available": not bool(item_row["deleted"])
            })

        result.append({
            "id": cart_id,
            "items": items,
            "price": row["total_price"]
        })

    return result


@api_router_cart.post('/{cart_id}/add/{item_id}', status_code=status.HTTP_200_OK)
async def add_item_to_cart(
    cart_id: int = Path(ge=1, description="ID корзины"),
    item_id: int = Path(ge=1, description="ID товара"),
    db: aiosqlite.Connection = Depends(get_conn)
):
    cart_exists = await db.execute("SELECT id FROM cart WHERE id = ?", (cart_id,))
    if not await cart_exists.fetchone():

        raise HTTPException(status_code=404, detail="Cart not found")

    item_exists = await db.execute("SELECT id FROM item WHERE id = ?", (item_id,))
    if not await item_exists.fetchone():

        raise HTTPException(status_code=404, detail="Item not found")

    existing = await db.execute(
        "SELECT quantity FROM cart_item WHERE cart_id = ? AND item_id = ?",
        (cart_id, item_id)
    )
    existing_row = await existing.fetchone()

    if existing_row:
        await db.execute(
            "UPDATE cart_item SET quantity = quantity + 1 WHERE cart_id = ? AND item_id = ?",
            (cart_id, item_id)
        )
    else:
        await db.execute(
            "INSERT INTO cart_item (cart_id, item_id, quantity) VALUES (?, ?, 1)",
            (cart_id, item_id)
        )

    await db.commit()
    return {"message": f"Item {item_id} added to cart {cart_id}"}


@api_router_item.post('/', status_code=status.HTTP_201_CREATED)
async def add_new_item(
    item_data: dict,
    db: aiosqlite.Connection = Depends(get_conn)
):
    cursor = await db.execute(
        "INSERT INTO item (name, price) VALUES (?, ?)",
        (item_data["name"], item_data["price"])
    )
    await db.commit()
    item_id = cursor.lastrowid

    row = await db.execute(
        "SELECT id, name, price, deleted FROM item WHERE id = ?",
        (item_id,)
    )
    result = await row.fetchone()
    return dict(result)


@api_router_item.get('/{id}', status_code=status.HTTP_200_OK)
async def get_item_by_id(
    id: int = Path(ge=0, description="ID товара"),
    db: aiosqlite.Connection = Depends(get_conn)
):
    cursor = await db.execute(
        "SELECT id, name, price, deleted FROM item WHERE id = ?",
        (id,)
    )
    result = await cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Item not found")

    if result["deleted"]:
        raise HTTPException(status_code=404, detail="Item not found")

    return dict(result)


@api_router_item.get('/', status_code=status.HTTP_200_OK)
async def get_items_params(
    offset: int = Query(0, ge=0, description="Смещение по списку"),
    limit: int = Query(10, ge=1, le=100, description="Ограничение на количество"),
    show_deleted: Optional[bool] = Query(False, description="Показывать удаленные товары"),
    min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена включительно"),
    max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена включительно"),
    db: aiosqlite.Connection = Depends(get_conn)
):
    query = "SELECT id, name, price, deleted FROM item WHERE 1=1"
    params = []

    if not show_deleted:
        query += " AND deleted = 0"

    if min_price is not None:
        query += " AND price >= ?"
        params.append(min_price)

    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)

    query += " ORDER BY id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    return [dict(row) for row in rows]


@api_router_item.put('/{id}', status_code=status.HTTP_200_OK)
async def replace_item_by_id(
    id: int = Path(ge=0, description='ID товара на замену'),
    item_data: dict = None,
    db: aiosqlite.Connection = Depends(get_conn)
):
    if not item_data or "name" not in item_data or "price" not in item_data:

        raise HTTPException(status_code=422, detail="Missing required fields")

    cursor = await db.execute(
        "SELECT id FROM item WHERE id = ?",
        (id,)
    )
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Item not found")

    await db.execute(
        "UPDATE item SET name = ?, price = ? WHERE id = ?",
        (item_data["name"], item_data["price"], id)
    )
    await db.commit()

    row = await db.execute(
        "SELECT id, name, price, deleted FROM item WHERE id = ?",
        (id,)
    )
    result = await row.fetchone()
    return dict(result)


@api_router_item.patch('/{id}', status_code=status.HTTP_200_OK)
async def edit_item_by_id(
    id: int = Path(ge=0, description='ID товара для редактирования'),
    item_data: dict = None,
    db: aiosqlite.Connection = Depends(get_conn)
):
    cursor = await db.execute(
        "SELECT id, name, price, deleted FROM item WHERE id = ?",
        (id,)
    )
    result = await cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Item not found")

    if result["deleted"]:
        raise HTTPException(status_code=304, detail="Item is deleted")

    if not item_data:
        return dict(result)

    if "deleted" in item_data:
        raise HTTPException(status_code=422, detail="Cannot modify deleted field")

    possible_fields = {'name', 'price'}
    for k in item_data.keys():
        if k not in possible_fields:
            raise HTTPException(status_code=422, detail="Invalid field")

    update_fields = []
    params = []

    if "name" in item_data:
        update_fields.append("name = ?")
        params.append(item_data["name"])

    if "price" in item_data:
        update_fields.append("price = ?")
        params.append(item_data["price"])

    if update_fields:
        params.append(id)
        await db.execute(
            f"UPDATE item SET {', '.join(update_fields)} WHERE id = ?",
            params
        )
        await db.commit()

        row = await db.execute(
            "SELECT id, name, price, deleted FROM item WHERE id = ?",
            (id,)
        )
        result = await row.fetchone()

    return dict(result)


@api_router_item.delete('/{id}', status_code=status.HTTP_200_OK)
async def delete_item_by_id(
    id: int = Path(ge=0, description='ID товара для редактирования'),
    db: aiosqlite.Connection = Depends(get_conn)
):
    cursor = await db.execute(
        "SELECT id, deleted FROM item WHERE id = ?",
        (id,)
    )

    item = await cursor.fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item["deleted"] == 1:
        return {"message": f"Item {id} already deleted"}

    await db.execute(
        "UPDATE item SET deleted = 1 WHERE id = ?",
        (id,)
    )
    await db.commit()

    return {"message": f"Item {id} deleted"}

app.include_router(api_router_cart)
app.include_router(api_router_item)
