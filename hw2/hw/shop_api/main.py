from fastapi import (
    FastAPI, APIRouter, Query, Path, Depends, HTTPException, status
)
from fastapi.responses import JSONResponse
from typing import Optional
from contextlib import asynccontextmanager
import asyncpg
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

conn: asyncpg.Connection | None = None

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS item (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  price REAL NOT NULL,
  deleted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cart (
  id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS cart_item (
  cart_id INTEGER NOT NULL,
  item_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (cart_id, item_id),
  FOREIGN KEY (cart_id) REFERENCES cart(id) ON DELETE CASCADE,
  FOREIGN KEY (item_id) REFERENCES item(id) ON DELETE CASCADE
);
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global conn
    conn = await asyncpg.connect(user="postgres", password="postgres", database="shop", host="db", port=5432)
    await conn.execute(SCHEMA_SQL)
    yield
    await conn.close()

app = FastAPI(title="Shop API", lifespan=lifespan)
api_router_cart = APIRouter(prefix='/cart')
api_router_item = APIRouter(prefix='/item')

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)


async def get_conn() -> asyncpg.Connection:
    global conn
    if conn is None or conn.is_closed():
        conn = await asyncpg.connect(user="postgres", password="postgres", database="shop", host="db", port=5432)
        await conn.execute(SCHEMA_SQL)
    return conn


@api_router_cart.post('/', status_code=status.HTTP_201_CREATED)
async def create_cart(db: asyncpg.Connection = Depends(get_conn)):
    cart_id = await db.fetchval("INSERT INTO cart DEFAULT VALUES RETURNING id")
    return JSONResponse(
        content={"id": cart_id},
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/cart/{cart_id}"},
    )


@api_router_cart.get('/{id}', status_code=status.HTTP_200_OK)
async def get_cart_by_id(
    id: int = Path(ge=0),
    db: asyncpg.Connection = Depends(get_conn)
):
    rows = await db.fetch("""
    SELECT
        c.id as cart_id,
        ci.item_id,
        ci.quantity,
        i.name,
        i.price,
        i.deleted
    FROM cart c
    LEFT JOIN cart_item ci ON c.id = ci.cart_id
    LEFT JOIN item i ON ci.item_id = i.id
    WHERE c.id = $1
    """, id)

    if not rows:
        raise HTTPException(status_code=404, detail="Cart not found")

    items = []
    total_price = 0.0
    for row in rows:
        if row["item_id"] is not None:
            item = {
                "id": row["item_id"],
                "name": row["name"],
                "quantity": row["quantity"],
                "available": not bool(row["deleted"])
            }
            items.append(item)
            if not row["deleted"]:
                total_price += row["price"] * row["quantity"]

    return {"id": id, "items": items, "price": total_price}


@api_router_cart.get('/', status_code=status.HTTP_200_OK)
async def get_carts_params(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    db: asyncpg.Connection = Depends(get_conn)
):
    base_query = """
    WITH agg AS (
      SELECT 
        c.id,
        COALESCE(SUM(CASE WHEN i.deleted = 0 THEN ci.quantity * i.price ELSE 0 END), 0) AS total_price,
        COALESCE(SUM(ci.quantity), 0) AS total_quantity
      FROM cart c
      LEFT JOIN cart_item ci ON c.id = ci.cart_id
      LEFT JOIN item i ON ci.item_id = i.id
      GROUP BY c.id
    )
    SELECT id, total_price, total_quantity
    FROM agg
    WHERE 1=1
    """

    conditions = []
    params: list = []

    if min_price is not None:
        conditions.append(f" AND total_price >= ${len(params) + 1}")
        params.append(min_price)

    if max_price is not None:
        conditions.append(f" AND total_price <= ${len(params) + 1}")
        params.append(max_price)

    if min_quantity is not None:
        conditions.append(f" AND total_quantity >= ${len(params) + 1}")
        params.append(min_quantity)

    if max_quantity is not None:
        conditions.append(f" AND total_quantity <= ${len(params) + 1}")
        params.append(max_quantity)

    conditions_sql = "".join(conditions)
    params.extend([limit, offset])
    query = base_query + conditions_sql + f" ORDER BY id LIMIT ${len(params) - 1} OFFSET ${len(params)}"

    rows = await db.fetch(query, *params)

    result = []
    for row in rows:
        cart_id = row["id"]
        items_rows = await db.fetch("""
            SELECT 
                ci.item_id,
                ci.quantity,
                i.name,
                i.price,
                i.deleted
            FROM cart_item ci
            LEFT JOIN item i ON ci.item_id = i.id
            WHERE ci.cart_id = $1
        """, cart_id)

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
    cart_id: int = Path(ge=1),
    item_id: int = Path(ge=1),
    db: asyncpg.Connection = Depends(get_conn)
):
    cart_exists = await db.fetchval("SELECT id FROM cart WHERE id = $1", cart_id)
    if not cart_exists:
        raise HTTPException(status_code=404, detail="Cart not found")
    item_exists = await db.fetchval("SELECT id FROM item WHERE id = $1", item_id)
    if not item_exists:
        raise HTTPException(status_code=404, detail="Item not found")
    existing_row = await db.fetchrow(
        "SELECT quantity FROM cart_item WHERE cart_id = $1 AND item_id = $2",
        cart_id, item_id
    )
    if existing_row:
        await db.execute(
            "UPDATE cart_item SET quantity = quantity + 1 WHERE cart_id = $1 AND item_id = $2",
            cart_id, item_id
        )
    else:
        await db.execute(
            "INSERT INTO cart_item (cart_id, item_id, quantity) VALUES ($1, $2, 1)",
            cart_id, item_id
        )
    return {"message": f"Item {item_id} added to cart {cart_id}"}


class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)


@api_router_item.post('/', status_code=status.HTTP_201_CREATED)
async def add_new_item(
    item_data: ItemCreate,
    db: asyncpg.Connection = Depends(get_conn)
):
    item_id = await db.fetchval(
        "INSERT INTO item (name, price) VALUES ($1, $2) RETURNING id",
        item_data.name, item_data.price
    )
    result = await db.fetchrow(
        "SELECT id, name, price, deleted FROM item WHERE id = $1",
        item_id
    )
    return dict(result)


@api_router_item.get('/{id}', status_code=status.HTTP_200_OK)
async def get_item_by_id(
    id: int = Path(ge=0),
    db: asyncpg.Connection = Depends(get_conn)
):
    result = await db.fetchrow(
        "SELECT id, name, price, deleted FROM item WHERE id = $1",
        id
    )
    if not result or result["deleted"]:
        raise HTTPException(status_code=404, detail="Item not found")
    return dict(result)


@api_router_item.get('/', status_code=status.HTTP_200_OK)
async def get_items_params(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    show_deleted: Optional[bool] = Query(False),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    db: asyncpg.Connection = Depends(get_conn)
):
    query = "SELECT id, name, price, deleted FROM item WHERE 1=1"
    params = []
    if not show_deleted:
        query += " AND deleted = 0"
    if min_price is not None:
        query += f" AND price >= ${len(params)+1}"
        params.append(min_price)
    if max_price is not None:
        query += f" AND price <= ${len(params)+1}"
        params.append(max_price)
    query += f" ORDER BY id LIMIT ${len(params)+1} OFFSET ${len(params)+2}"
    params.extend([limit, offset])
    rows = await db.fetch(query, *params)
    return [dict(row) for row in rows]


class ItemReplace(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)


@api_router_item.put('/{id}', status_code=status.HTTP_200_OK)
async def replace_item_by_id(
    id: int = Path(ge=0),
    item_data: ItemReplace = None,
    db: asyncpg.Connection = Depends(get_conn)
):
    if item_data is None:
        raise HTTPException(status_code=422, detail="Missing required fields")
    exists = await db.fetchval("SELECT id FROM item WHERE id = $1", id)
    if not exists:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.execute(
        "UPDATE item SET name = $1, price = $2 WHERE id = $3",
        item_data.name, item_data.price, id
    )
    result = await db.fetchrow(
        "SELECT id, name, price, deleted FROM item WHERE id = $1",
        id
    )
    return dict(result)


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(min_length=1)
    price: Optional[float] = Field(gt=0)


@api_router_item.patch('/{id}', status_code=status.HTTP_200_OK)
async def edit_item_by_id(
    id: int = Path(ge=0),
    item_data: Optional[ItemUpdate] = None,
    db: asyncpg.Connection = Depends(get_conn)
):
    result = await db.fetchrow(
        "SELECT id, name, price, deleted FROM item WHERE id = $1",
        id
    )
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    if result["deleted"]:
        raise HTTPException(status_code=304, detail="Item is deleted")
    if not item_data:
        return dict(result)
    if item_data.name:
        await db.execute("UPDATE item SET name = $1 WHERE id = $2", item_data.name, id)
    if item_data.price:
        await db.execute("UPDATE item SET price = $1 WHERE id = $2", item_data.price, id)
    result = await db.fetchrow(
        "SELECT id, name, price, deleted FROM item WHERE id = $1",
        id
    )
    return dict(result)


@api_router_item.delete('/{id}', status_code=status.HTTP_200_OK)
async def delete_item_by_id(
    id: int = Path(ge=0),
    db: asyncpg.Connection = Depends(get_conn)
):
    item = await db.fetchrow("SELECT id, deleted FROM item WHERE id = $1", id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item["deleted"] == 1:
        return {"message": f"Item {id} already deleted"}
    await db.execute("UPDATE item SET deleted = 1 WHERE id = $1", id)
    return {"message": f"Item {id} deleted"}


app.include_router(api_router_cart)
app.include_router(api_router_item)
