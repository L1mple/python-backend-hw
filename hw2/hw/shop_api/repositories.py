from __future__ import annotations

from sqlite3 import Connection, Row
from typing import Dict, List, Optional, Tuple

from .database import Cart, CartItem, Item
from .exceptions import ItemDeletedError, ItemNotFoundError


class ItemRepository:
    def __init__(self, connection: Connection) -> None:
        self._conn = connection

    def _row_to_item(self, row: Row) -> Item:
        return Item(
            id=row["id"],
            name=row["name"],
            price=float(row["price"]),
            deleted=bool(row["deleted"]),
        )

    def _fetch_item(self, item_id: int, *, include_deleted: bool) -> Item:
        row = self._conn.execute(
            "SELECT id, name, price, deleted FROM items WHERE id = ?",
            (item_id,),
        ).fetchone()

        if row is None:
            raise ItemNotFoundError

        item = self._row_to_item(row)
        if item.deleted and not include_deleted:
            raise ItemNotFoundError

        return item

    def create(self, name: str, price: float) -> Item:
        cursor = self._conn.execute(
            "INSERT INTO items (name, price, deleted) VALUES (?, ?, 0)",
            (name, price),
        )
        self._conn.commit()
        return self._fetch_item(cursor.lastrowid, include_deleted=True)

    def get(self, item_id: int, include_deleted: bool = False) -> Item:
        return self._fetch_item(item_id, include_deleted=include_deleted)

    def list(
        self,
        *,
        offset: int = 0,
        limit: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        show_deleted: bool = False,
    ) -> List[Item]:
        clauses = []
        params: List[object] = []

        if not show_deleted:
            clauses.append("deleted = 0")
        if min_price is not None:
            clauses.append("price >= ?")
            params.append(min_price)
        if max_price is not None:
            clauses.append("price <= ?")
            params.append(max_price)

        sql = "SELECT id, name, price, deleted FROM items"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id"

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
            if offset:
                sql += " OFFSET ?"
                params.append(offset)
        elif offset:
            sql += " LIMIT -1 OFFSET ?"
            params.append(offset)

        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_item(row) for row in rows]

    def update(self, item_id: int, *, name: str, price: float) -> Item:
        item = self._fetch_item(item_id, include_deleted=True)
        if item.deleted:
            raise ItemDeletedError

        self._conn.execute(
            "UPDATE items SET name = ?, price = ? WHERE id = ?",
            (name, price, item_id),
        )
        self._conn.commit()
        return self._fetch_item(item_id, include_deleted=True)

    def patch(
        self,
        item_id: int,
        *,
        name: Optional[str],
        price: Optional[float],
    ) -> Item:
        item = self._fetch_item(item_id, include_deleted=True)
        if item.deleted:
            raise ItemDeletedError

        updates: List[str] = []
        params: List[object] = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if price is not None:
            updates.append("price = ?")
            params.append(price)

        if updates:
            params.append(item_id)
            self._conn.execute(
                f"UPDATE items SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            self._conn.commit()

        return self._fetch_item(item_id, include_deleted=True)

    def delete(self, item_id: int) -> None:
        item = self._fetch_item(item_id, include_deleted=True)

        if item.deleted:
            return

        self._conn.execute(
            "UPDATE items SET deleted = 1 WHERE id = ?",
            (item_id,),
        )
        self._conn.commit()


class CartRepository:
    def __init__(self, connection: Connection, item_repo: ItemRepository) -> None:
        self._conn = connection
        self._item_repo = item_repo

    def create(self) -> Cart:
        cursor = self._conn.execute("INSERT INTO carts DEFAULT VALUES")
        cart_id = cursor.lastrowid
        self._conn.commit()
        return Cart(id=cart_id)

    def _build_cart(self, cart_id: int) -> Cart:
        return Cart(id=cart_id, items=self._fetch_cart_items(cart_id))

    def _fetch_cart_items(self, cart_id: int) -> Dict[int, CartItem]:
        rows = self._conn.execute(
            "SELECT item_id, quantity FROM cart_items WHERE cart_id = ?",
            (cart_id,),
        ).fetchall()
        return {
            row["item_id"]: CartItem(
                item_id=row["item_id"],
                quantity=int(row["quantity"]),
            )
            for row in rows
        }

    def get(self, cart_id: int) -> Cart:
        cart_row = self._conn.execute(
            "SELECT id FROM carts WHERE id = ?",
            (cart_id,),
        ).fetchone()
        if cart_row is None:
            raise KeyError(cart_id)

        return self._build_cart(cart_id)

    def list(
        self,
        *,
        offset: int = 0,
        limit: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
    ) -> List[Cart]:
        params: List[object] = []
        query = "SELECT id FROM carts ORDER BY id"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
            if offset:
                query += " OFFSET ?"
                params.append(offset)
        elif offset:
            query += " LIMIT -1 OFFSET ?"
            params.append(offset)

        rows = self._conn.execute(query, params).fetchall()

        carts: List[Cart] = []
        for row in rows:
            cart_id = row["id"]
            total_price, total_quantity = self._get_cart_metrics(cart_id)

            if min_price is not None and total_price < min_price:
                continue
            if max_price is not None and total_price > max_price:
                continue
            if min_quantity is not None and total_quantity < min_quantity:
                continue
            if max_quantity is not None and total_quantity > max_quantity:
                continue

            carts.append(self._build_cart(cart_id))

        return carts

    def add_item(self, cart_id: int, item_id: int) -> None:
        cart_exists = self._conn.execute(
            "SELECT 1 FROM carts WHERE id = ?",
            (cart_id,),
        ).fetchone()
        if cart_exists is None:
            raise KeyError(cart_id)

        item = self._item_repo.get(item_id)

        self._conn.execute(
            """
            INSERT INTO cart_items (cart_id, item_id, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(cart_id, item_id)
            DO UPDATE SET quantity = quantity + 1
            """,
            (cart_id, item.id),
        )
        self._conn.commit()

    def calculate_total(self, cart: Cart) -> float:
        total_price, _ = self._get_cart_metrics(cart.id)
        return total_price

    def _get_cart_metrics(self, cart_id: int) -> Tuple[float, int]:
        row = self._conn.execute(
            """
            SELECT
                COALESCE(SUM(i.price * ci.quantity), 0.0) AS total_price,
                COALESCE(SUM(ci.quantity), 0) AS total_quantity
            FROM cart_items AS ci
            JOIN items AS i ON i.id = ci.item_id
            WHERE ci.cart_id = ?
              AND i.deleted = 0
            """,
            (cart_id,),
        ).fetchone()

        if row is None:
            return 0.0, 0

        total_price = float(row["total_price"] or 0.0)
        total_quantity = int(row["total_quantity"] or 0)

        return total_price, total_quantity