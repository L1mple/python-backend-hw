"""SQLAlchemy sync storage adapter для items и carts."""

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    Text,
    Numeric,
    Boolean,
    ForeignKey,
)
from sqlalchemy.sql import select
import os
from fastapi import Request

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://test-user:test-pass@localhost:5542/test-db"
)

engine = None
metadata = MetaData()

items = Table(
    "items",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", Text, nullable=False),
    Column("price", Numeric, nullable=False),
    Column("description", Text),
    Column("deleted", Boolean, nullable=False, default=False),
)

carts = Table(
    "carts",
    metadata,
    Column("id", Integer, primary_key=True),
)

cart_lines = Table(
    "cart_lines",
    metadata,
    Column(
        "cart_id", Integer, ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "item_id",
        Integer,
        ForeignKey("items.id", ondelete="SET NULL"),
        primary_key=True,
    ),
    Column("quantity", Integer, nullable=False, default=1),
)


def init_engine():
    global engine
    if engine is None:
        engine = create_engine(DATABASE_URL)


def create_schema():
    init_engine()
    metadata.create_all(engine)


def drop_schema():
    init_engine()
    metadata.drop_all(engine)


def get_store(request: Request):
    init_engine()
    return engine, {}, None


def list_items(offset=0, limit=10, min_price=None, max_price=None, show_deleted=False):
    init_engine()
    with engine.connect() as conn:
        stmt = select(items)
        conditions = []
        if not show_deleted:
            conditions.append(items.c.deleted == False)
        if min_price is not None:
            conditions.append(items.c.price >= min_price)
        if max_price is not None:
            conditions.append(items.c.price <= max_price)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.offset(offset).limit(limit)
        rows = conn.execute(stmt).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "name": r.name,
                "price": float(r.price),
                "description": r.description,
                "deleted": r.deleted,
            }
        )
    return out


def get_item(item_id: int):
    init_engine()
    with engine.connect() as conn:
        stmt = select(items).where(items.c.id == item_id)
        r = conn.execute(stmt).fetchone()
        if not r:
            return None
        return {
            "id": r.id,
            "name": r.name,
            "price": float(r.price),
            "description": r.description,
            "deleted": r.deleted,
        }


def get_items_by_ids(ids: list[int]) -> list[dict]:
    """Return list of item dicts matching provided ids."""
    if not ids:
        return []
    init_engine()
    with engine.connect() as conn:
        stmt = select(items).where(items.c.id.in_(ids))
        rows = conn.execute(stmt).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "name": r.name,
                "price": float(r.price),
                "description": r.description,
                "deleted": r.deleted,
            }
        )
    return out


def create_item(name: str, price: float, description: str | None):
    init_engine()
    with engine.connect() as conn:
        res = conn.execute(
            items.insert()
            .values(name=name, price=price, description=description)
            .returning(items)
        )
        row = res.fetchone()
        conn.commit()
        return {
            "id": row.id,
            "name": row.name,
            "price": float(row.price),
            "description": row.description,
            "deleted": row.deleted,
        }


def update_item(item_id: int, name: str, price: float, description: str | None):
    init_engine()
    with engine.connect() as conn:
        res = conn.execute(
            items.update()
            .where(items.c.id == item_id)
            .values(name=name, price=price, description=description, deleted=False)
            .returning(items)
        )
        row = res.fetchone()
        if not row:
            return None
        conn.commit()
        return {
            "id": row.id,
            "name": row.name,
            "price": float(row.price),
            "description": row.description,
            "deleted": row.deleted,
        }


def patch_item(item_id: int, patch: dict):
    cur = get_item(item_id)
    if not cur:
        return None
    name = patch.get("name", cur["name"])
    price = patch.get("price", cur["price"])
    description = patch.get("description", cur["description"])
    return update_item(item_id, name, price, description)


def delete_item(item_id: int):
    init_engine()
    with engine.connect() as conn:
        res = conn.execute(
            items.update()
            .where(items.c.id == item_id)
            .values(deleted=True)
            .returning(items)
        )
        row = res.fetchone()
        if not row:
            return None
        conn.commit()
        return {
            "id": row.id,
            "name": row.name,
            "price": float(row.price),
            "description": row.description,
            "deleted": row.deleted,
        }


# carts


def create_cart():
    init_engine()
    with engine.connect() as conn:
        res = conn.execute(carts.insert().returning(carts.c.id))
        cid = res.fetchone()[0]
        conn.commit()
        return cid


def get_cart(cart_id: int):
    init_engine()
    with engine.connect() as conn:
        res = conn.execute(
            select(cart_lines).where(cart_lines.c.cart_id == cart_id)
        ).fetchall()
        if not res:
            r = conn.execute(select(carts).where(carts.c.id == cart_id)).fetchone()
            if not r:
                return None
        cart = {r.item_id: r.quantity for r in res}
        return cart


def list_carts():
    init_engine()
    with engine.connect() as conn:
        res = conn.execute(select(carts)).fetchall()
        outs = []
        for r in res:
            cid = r.id
            cart = get_cart(cid) or {}
            outs.append({"id": cid, "cart": cart})
        return outs


def add_to_cart(cart_id: int, item_id: int):
    init_engine()
    with engine.connect() as conn:
        r = conn.execute(
            select(items.c.id, items.c.deleted).where(items.c.id == item_id)
        ).fetchone()
        if not r:
            return None
        if r.deleted:
            raise ValueError("item deleted")
        existing = conn.execute(
            select(cart_lines.c.quantity)
            .where(cart_lines.c.cart_id == cart_id)
            .where(cart_lines.c.item_id == item_id)
        ).fetchone()
        if existing:
            conn.execute(
                cart_lines.update()
                .where(cart_lines.c.cart_id == cart_id)
                .where(cart_lines.c.item_id == item_id)
                .values(quantity=cart_lines.c.quantity + 1)
            )
        else:
            conn.execute(
                cart_lines.insert().values(cart_id=cart_id, item_id=item_id, quantity=1)
            )
        conn.commit()
    return get_cart(cart_id)
