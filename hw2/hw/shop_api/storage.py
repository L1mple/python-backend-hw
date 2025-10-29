from typing import Any, Dict, Optional
import os

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Boolean,
    Numeric,
    ForeignKey,
    select,
    insert,
    update as sa_update,
    func,
)
from sqlalchemy.engine import Engine


class Storage:
    def __init__(self):
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://shop_user:shop_password@localhost:5432/shop_db",
        )
        print(f"Database URL: {database_url}")
        self.engine: Engine = create_engine(database_url, future=True)
        self.metadata = MetaData()

        self.items = Table(
            "items",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String, nullable=False),
            Column("price", Numeric, nullable=False),
            Column("deleted", Boolean, nullable=False, server_default="false"),
        )

        self.carts = Table(
            "carts",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
        )

        self.cart_items = Table(
            "cart_items",
            self.metadata,
            Column("cart_id", Integer, ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True),
            Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
            Column("quantity", Integer, nullable=False),
        )

        with self.engine.begin() as conn:
            self.metadata.create_all(conn)

    def get_item_by_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(
                    self.items.c.id,
                    self.items.c.name,
                    self.items.c.price,
                    self.items.c.deleted,
                ).where(self.items.c.id == item_id)
            ).mappings().first()
            return dict(row) if row else None

    def get_cart_by_id(self, cart_id: int) -> Optional[Dict[str, Any]]:
        with self.engine.begin() as conn:
            cart_row = conn.execute(
                select(self.carts.c.id).where(self.carts.c.id == cart_id)
            ).mappings().first()
            if not cart_row:
                return None
            items_rows = conn.execute(
                select(self.cart_items.c.item_id, self.cart_items.c.quantity).where(
                    self.cart_items.c.cart_id == cart_id
                )
            ).all()
            items_map: Dict[str, int] = {str(r.item_id): r.quantity for r in items_rows}
            return {"id": cart_row["id"], "items": items_map}

    def create_item(self, item_data: Dict[str, Any]) -> int:
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(self.items).values(
                    name=item_data["name"], price=item_data["price"], deleted=False
                ).returning(self.items.c.id)
            )
            new_id = result.scalar_one()
            return int(new_id)

    def create_cart(self) -> int:
        with self.engine.begin() as conn:
            result = conn.execute(insert(self.carts).values().returning(self.carts.c.id))
            new_id = result.scalar_one()
            return int(new_id)

    def update_item(self, item_id: int, update_data: Dict[str, Any]) -> None:
        values: Dict[str, Any] = {}
        if "name" in update_data and update_data["name"] is not None:
            values["name"] = update_data["name"]
        if "price" in update_data and update_data["price"] is not None:
            values["price"] = update_data["price"]
        if not values:
            return
        with self.engine.begin() as conn:
            conn.execute(
                sa_update(self.items).where(self.items.c.id == item_id).values(**values)
            )

    def delete_item(self, item_id: int) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                sa_update(self.items)
                .where(self.items.c.id == item_id)
                .values(deleted=True)
            )

    def add_item_to_cart(self, cart_id: int, item_id: int) -> None:
        with self.engine.begin() as conn:
            current = conn.execute(
                select(self.cart_items.c.quantity).where(
                    (self.cart_items.c.cart_id == cart_id)
                    & (self.cart_items.c.item_id == item_id)
                )
            ).scalar_one_or_none()
            if current is None:
                conn.execute(
                    insert(self.cart_items).values(
                        cart_id=cart_id, item_id=item_id, quantity=1
                    )
                )
            else:
                conn.execute(
                    sa_update(self.cart_items)
                    .where(
                        (self.cart_items.c.cart_id == cart_id)
                        & (self.cart_items.c.item_id == item_id)
                    )
                    .values(quantity=current + 1)
                )

    def get_all_items(self) -> list[Dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(
                    self.items.c.id, self.items.c.name, self.items.c.price, self.items.c.deleted
                )
            ).mappings().all()
            return [dict(r) for r in rows]

    def get_all_carts(self) -> list[Dict[str, Any]]:
        with self.engine.begin() as conn:
            cart_rows = conn.execute(select(self.carts.c.id)).mappings().all()
            result: list[Dict[str, Any]] = []
            for row in cart_rows:
                cart_id = row["id"]
                items_rows = conn.execute(
                    select(self.cart_items.c.item_id, self.cart_items.c.quantity).where(
                        self.cart_items.c.cart_id == cart_id
                    )
                ).all()
                items_map: Dict[str, int] = {str(r.item_id): r.quantity for r in items_rows}
                result.append({"id": cart_id, "items": items_map})
            return result

    def calculate_cart_price(self, cart: Dict[str, Any]) -> float:
        if not cart.get("items"):
            return 0.0
        item_ids = [int(k) for k in cart["items"].keys()]
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(self.items.c.id, self.items.c.price, self.items.c.deleted).where(
                    self.items.c.id.in_(item_ids)
                )
            ).all()
            price_map = {r.id: (float(r.price), bool(r.deleted)) for r in rows}
            total = 0.0
            for item_id_str, quantity in cart["items"].items():
                item_id_int = int(item_id_str)
                if item_id_int in price_map and not price_map[item_id_int][1]:
                    total += price_map[item_id_int][0] * int(quantity)
            return total


storage = Storage()
