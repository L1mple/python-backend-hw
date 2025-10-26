from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .schemas import Cart, CartItem, Item


_connection: Optional[sqlite3.Connection] = None
_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    if _connection is None:
        raise RuntimeError("Database is not initialized. Call init_db() at startup.")
    return _connection


def init_db(db_path: str | Path = "shop.db") -> None:
    global _connection
    if _connection is not None:
        return
    path = str(db_path)
    _connection = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    _connection.row_factory = sqlite3.Row
    with _connection:
        _connection.execute("PRAGMA foreign_keys=ON;")
        _connection.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0),
                deleted INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        _connection.execute(
            """
            CREATE TABLE IF NOT EXISTS carts (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            );
            """
        )
        _connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cart_items (
                cart_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity >= 1),
                PRIMARY KEY (cart_id, item_id),
                FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
            );
            """
        )


# ---------- Item operations ----------


def create_item(name: str, price: float) -> Item:
    with _lock, _conn():
        cur = _conn().execute(
            "INSERT INTO items(name, price, deleted) VALUES(?, ?, 0)", (name, float(price))
        )
        item_id = int(cur.lastrowid)
        row = _conn().execute(
            "SELECT id, name, price, deleted FROM items WHERE id = ?", (item_id,)
        ).fetchone()
    return Item(id=row["id"], name=row["name"], price=float(row["price"]), deleted=bool(row["deleted"]))


def _row_to_item(row: sqlite3.Row) -> Item:
    return Item(id=row["id"], name=row["name"], price=float(row["price"]), deleted=bool(row["deleted"]))


def get_item(item_id: int, include_deleted: bool = False) -> Optional[Item]:
    row = _conn().execute(
        "SELECT id, name, price, deleted FROM items WHERE id = ?", (item_id,)
    ).fetchone()
    if row is None:
        return None
    item = _row_to_item(row)
    if not include_deleted and item.deleted:
        return None
    return item


def list_items(
    *,
    offset: int,
    limit: int,
    min_price: Optional[float],
    max_price: Optional[float],
    show_deleted: bool,
) -> List[Item]:
    clauses: list[str] = []
    params: list[object] = []
    if not show_deleted:
        clauses.append("deleted = 0")
    if min_price is not None:
        clauses.append("price >= ?")
        params.append(float(min_price))
    if max_price is not None:
        clauses.append("price <= ?")
        params.append(float(max_price))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    query = f"SELECT id, name, price, deleted FROM items{where} ORDER BY id LIMIT ? OFFSET ?"
    params.extend([int(limit), int(offset)])
    rows = _conn().execute(query, params).fetchall()
    return [_row_to_item(r) for r in rows]


def replace_item(item_id: int, name: str, price: float) -> Optional[Item]:
    with _lock:
        row = _conn().execute("SELECT deleted FROM items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return None
        if bool(row["deleted"]):
            return None
        _conn().execute("UPDATE items SET name = ?, price = ? WHERE id = ?", (name, float(price), item_id))
    return get_item(item_id, include_deleted=True)


def patch_item(item_id: int, *, name: Optional[str], price: Optional[float]) -> Tuple[str, Optional[Item]]:
    # Returns (status, item). status in {"ok", "deleted", "not_found"}
    with _lock:
        row = _conn().execute("SELECT id, name, price, deleted FROM items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return "not_found", None
        if bool(row["deleted"]):
            return "deleted", None
        new_name = name if name is not None else row["name"]
        new_price = float(price) if price is not None else float(row["price"])
        _conn().execute("UPDATE items SET name = ?, price = ? WHERE id = ?", (new_name, new_price, item_id))
    return "ok", get_item(item_id, include_deleted=True)


def soft_delete_item(item_id: int) -> None:
    with _lock:
        _conn().execute("UPDATE items SET deleted = 1 WHERE id = ?", (item_id,))


# ---------- Cart operations ----------


def create_cart() -> int:
    with _lock:
        cur = _conn().execute("INSERT INTO carts DEFAULT VALUES")
        return int(cur.lastrowid)


def _get_cart_items_map(cart_id: int) -> Optional[dict[int, int]]:
    exists = _conn().execute("SELECT 1 FROM carts WHERE id = ?", (cart_id,)).fetchone()
    if exists is None:
        return None
    rows = _conn().execute(
        "SELECT item_id, quantity FROM cart_items WHERE cart_id = ? ORDER BY item_id",
        (cart_id,),
    ).fetchall()
    return {int(r["item_id"]): int(r["quantity"]) for r in rows}


def compute_cart_price(cart_map: dict[int, int]) -> float:
    total = 0.0
    if not cart_map:
        return total
    item_ids = tuple(cart_map.keys())
    placeholders = ",".join(["?"] * len(item_ids))
    rows = _conn().execute(
        f"SELECT id, price, deleted FROM items WHERE id IN ({placeholders})",
        item_ids,
    ).fetchall()
    id_to_price_deleted = {int(r["id"]): (float(r["price"]), bool(r["deleted"])) for r in rows}
    for iid, qty in cart_map.items():
        price_deleted = id_to_price_deleted.get(iid)
        if price_deleted is None:
            continue
        price, deleted = price_deleted
        if deleted:
            continue
        total += price * qty
    return total


def cart_to_model(cart_id: int) -> Optional[Cart]:
    cart_map = _get_cart_items_map(cart_id)
    if cart_map is None:
        return None
    items = [CartItem(id=iid, quantity=qty) for iid, qty in cart_map.items()]
    return Cart(id=cart_id, items=items, price=compute_cart_price(cart_map))


def list_carts(
    *,
    offset: int,
    limit: int,
    min_price: Optional[float],
    max_price: Optional[float],
    min_quantity: Optional[int],
    max_quantity: Optional[int],
) -> List[Cart]:
    # Build full list, then filter in Python to keep logic close to original
    rows = _conn().execute("SELECT id FROM carts ORDER BY id").fetchall()
    carts: List[Cart] = []
    for r in rows:
        model = cart_to_model(int(r["id"]))
        if model is not None:
            carts.append(model)
    if min_price is not None:
        carts = [c for c in carts if c.price >= min_price]
    if max_price is not None:
        carts = [c for c in carts if c.price <= max_price]

    def qsum(c: Cart) -> int:
        return sum(ci.quantity for ci in c.items)

    if min_quantity is not None:
        carts = [c for c in carts if qsum(c) >= min_quantity]
    if max_quantity is not None:
        carts = [c for c in carts if qsum(c) <= max_quantity]

    return carts[offset : offset + limit]


def add_to_cart(cart_id: int, item_id: int) -> Optional[Cart]:
    with _lock:
        # Validate cart
        exist = _conn().execute("SELECT 1 FROM carts WHERE id = ?", (cart_id,)).fetchone()
        if exist is None:
            return None
        # Validate item and not deleted
        row = _conn().execute("SELECT deleted FROM items WHERE id = ?", (item_id,)).fetchone()
        if row is None or bool(row["deleted"]):
            # Item not available
            raise KeyError("item_not_found")
        # Upsert quantity
        cur = _conn().execute(
            "SELECT quantity FROM cart_items WHERE cart_id = ? AND item_id = ?",
            (cart_id, item_id),
        )
        r = cur.fetchone()
        if r is None:
            _conn().execute(
                "INSERT INTO cart_items(cart_id, item_id, quantity) VALUES(?, ?, 1)",
                (cart_id, item_id),
            )
        else:
            _conn().execute(
                "UPDATE cart_items SET quantity = ? WHERE cart_id = ? AND item_id = ?",
                (int(r["quantity"]) + 1, cart_id, item_id),
            )
    return cart_to_model(cart_id)

