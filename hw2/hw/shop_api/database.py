from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from functools import lru_cache
from sqlite3 import Connection
from typing import Dict, List

DB_URI = ":memory:"  # shared in-memory SQLite database


@dataclass
class Item:
    id: int
    name: str
    price: float
    deleted: bool = False


@dataclass
class CartItem:
    item_id: int
    quantity: int = 0


@dataclass
class Cart:
    id: int
    items: Dict[int, CartItem] = field(default_factory=dict)

    @property
    def items_list(self) -> List[CartItem]:
        return list(self.items.values())


def _initialize_schema(connection: Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS items (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL,
            price   REAL NOT NULL,
            deleted INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS carts (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        );

        CREATE TABLE IF NOT EXISTS cart_items (
            cart_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            PRIMARY KEY (cart_id, item_id),
            FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id)
        );
        """
    )
    connection.commit()


@lru_cache
def get_connection() -> Connection:
    connection = sqlite3.connect(DB_URI, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    _initialize_schema(connection)
    return connection