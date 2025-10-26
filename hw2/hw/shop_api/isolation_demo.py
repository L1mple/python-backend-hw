from __future__ import annotations

import threading
from decimal import Decimal
from typing import Any, Iterable

import psycopg
from psycopg.errors import SerializationFailure


def _normalize_url(url: str) -> str:
    if "+psycopg" in url:
        return url.replace("+psycopg", "", 1)
    return url


class IsolationDemo:
    DEMO_PREFIX = "Isolation Demo"
    _SUPPORTED_LEVELS = {
        "READ UNCOMMITTED",
        "READ COMMITTED",
        "REPEATABLE READ",
        "SERIALIZABLE",
    }

    def __init__(self) -> None:
        self.dsn = "postgresql://shop:shop@localhost:5432/shop"
        self.anchor_name = f"{self.DEMO_PREFIX} Anchor Item"
        self.anchor_item_id: int | None = None
        self._cleanup_demo_data()
        self.anchor_item_id = self._insert_item(self.anchor_name, 100.0)

    def _cleanup_demo_data(self) -> None:
        pattern = f"{self.DEMO_PREFIX}%"
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM cart_items
                    WHERE item_id IN (SELECT id FROM items WHERE name LIKE %s)
                    """,
                    (pattern,),
                )
                cur.execute(
                    "DELETE FROM items WHERE name LIKE %s",
                    (pattern,),
                )
        self.anchor_item_id = None

    def _start_transaction(self, isolation_level: str):
        if isolation_level not in self._SUPPORTED_LEVELS:
            raise ValueError(f"Unsupported isolation level: {isolation_level}")
        conn = psycopg.connect(self.dsn)
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
        return conn

    def _insert_item(self, name: str, price: float) -> int:
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO items (name, price, deleted)
                    VALUES (%s, %s, false)
                    RETURNING id
                    """,
                    (name, price),
                )
                return cur.fetchone()[0]

    def _delete_items(self, item_ids: Iterable[int]) -> None:
        ids = [item_id for item_id in item_ids if item_id is not None]
        if not ids:
            return
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM cart_items WHERE item_id = ANY(%s)",
                    (ids,),
                )
                cur.execute(
                    "DELETE FROM items WHERE id = ANY(%s)",
                    (ids,),
                )

    def _set_anchor_price(self, price: float) -> None:
        if self.anchor_item_id is None:
            raise RuntimeError("Anchor item is not initialized.")
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE items SET price = %s, deleted = false WHERE id = %s",
                    (price, self.anchor_item_id),
                )

    def _current_anchor_price(self) -> float:
        if self.anchor_item_id is None:
            raise RuntimeError("Anchor item is not initialized.")
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT price FROM items WHERE id = %s", (self.anchor_item_id,))
                raw = cur.fetchone()[0]
                return float(raw) if isinstance(raw, Decimal) else raw

    def _seed_price_band(self, prices: list[float], label: str) -> list[int]:
        ids: list[int] = []
        for idx, price in enumerate(prices, start=1):
            ids.append(self._insert_item(f"{self.DEMO_PREFIX} {label} {idx}", price))
        return ids

    def dirty_read_with_read_uncommitted(self) -> None:
        print("\n[1] Dirty read attempt with READ UNCOMMITTED (items table)")
        self._set_anchor_price(100.0)
        writer_ready = threading.Event()
        reader_done = threading.Event()
        observation: dict[str, Any] = {}

        def writer() -> None:
            conn = self._start_transaction("READ UNCOMMITTED")
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE items SET price = %s WHERE id = %s",
                        (999.0, self.anchor_item_id),
                    )
                writer_ready.set()
                reader_done.wait()
                conn.rollback()
            finally:
                conn.close()

        def reader() -> None:
            writer_ready.wait()
            conn = self._start_transaction("READ UNCOMMITTED")
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT price FROM items WHERE id = %s", (self.anchor_item_id,))
                    value = cur.fetchone()[0]
                    observation["during"] = float(value) if isinstance(value, Decimal) else value
                conn.rollback()
            finally:
                conn.close()
            reader_done.set()

        threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_value = self._current_anchor_price()
        dirty_seen = observation.get("during")
        print(f"  Reader saw price: {dirty_seen}")
        print(f"  Price after rollback: {final_value}")
        if dirty_seen == 999.0:
            print("  -> Dirty read observed (reader saw uncommitted data).")
        else:
            print(
                "  -> PostgreSQL upgrades READ UNCOMMITTED to READ COMMITTED, so dirty reads "
                "do not occur even if requested."
            )

    def clean_read_with_read_committed(self) -> None:
        print("\n[2] Dirty read prevention with READ COMMITTED")
        self._set_anchor_price(100.0)
        writer_ready = threading.Event()
        reader_done = threading.Event()
        observation: dict[str, Any] = {}

        def writer() -> None:
            conn = self._start_transaction("READ COMMITTED")
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE items SET price = %s WHERE id = %s",
                        (555.0, self.anchor_item_id),
                    )
                writer_ready.set()
                reader_done.wait()
                conn.rollback()
            finally:
                conn.close()

        def reader() -> None:
            writer_ready.wait()
            conn = self._start_transaction("READ COMMITTED")
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT price FROM items WHERE id = %s", (self.anchor_item_id,))
                    value = cur.fetchone()[0]
                    observation["during"] = float(value) if isinstance(value, Decimal) else value
                conn.rollback()
            finally:
                conn.close()
            reader_done.set()

        threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print(f"  Reader saw price: {observation.get('during')} (should still be 100.0)")
        print("  -> No dirty read under READ COMMITTED.")

    def non_repeatable_read_in_read_committed(self) -> None:
        print("\n[3] Non-repeatable read in READ COMMITTED")
        self._set_anchor_price(100.0)
        first_read_done = threading.Event()
        update_committed = threading.Event()
        observation: dict[str, Any] = {}

        def reader() -> None:
            conn = self._start_transaction("READ COMMITTED")
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT price FROM items WHERE id = %s", (self.anchor_item_id,))
                    value = cur.fetchone()[0]
                    observation["first"] = float(value) if isinstance(value, Decimal) else value
                first_read_done.set()
                update_committed.wait()
                with conn.cursor() as cur:
                    cur.execute("SELECT price FROM items WHERE id = %s", (self.anchor_item_id,))
                    value = cur.fetchone()[0]
                    observation["second"] = float(value) if isinstance(value, Decimal) else value
                conn.commit()
            finally:
                conn.close()

        def writer() -> None:
            first_read_done.wait()
            conn = self._start_transaction("READ COMMITTED")
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE items SET price = %s WHERE id = %s",
                        (200.0, self.anchor_item_id),
                    )
                conn.commit()
            finally:
                conn.close()
            update_committed.set()

        threads = [threading.Thread(target=reader), threading.Thread(target=writer)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print(f"  First read: {observation.get('first')}")
        print(f"  Second read: {observation.get('second')}")
        if observation.get("first") != observation.get("second"):
            print("  -> Non-repeatable read reproduced.")
        else:
            print("  -> Unexpected: values matched (try rerunning).")
        self._set_anchor_price(100.0)

    def repeatable_read_prevents_non_repeatable(self) -> None:
        print("\n[4] Repeatable read snapshot remains stable")
        self._set_anchor_price(100.0)
        first_read_done = threading.Event()
        update_committed = threading.Event()
        observation: dict[str, Any] = {}

        def reader() -> None:
            conn = self._start_transaction("REPEATABLE READ")
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT price FROM items WHERE id = %s", (self.anchor_item_id,))
                    value = cur.fetchone()[0]
                    observation["first"] = float(value) if isinstance(value, Decimal) else value
                first_read_done.set()
                update_committed.wait()
                with conn.cursor() as cur:
                    cur.execute("SELECT price FROM items WHERE id = %s", (self.anchor_item_id,))
                    value = cur.fetchone()[0]
                    observation["second"] = float(value) if isinstance(value, Decimal) else value
                conn.commit()
            finally:
                conn.close()

        def writer() -> None:
            first_read_done.wait()
            conn = self._start_transaction("READ COMMITTED")
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE items SET price = %s WHERE id = %s",
                        (321.0, self.anchor_item_id),
                    )
                conn.commit()
            finally:
                conn.close()
            update_committed.set()

        threads = [threading.Thread(target=reader), threading.Thread(target=writer)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print(f"  First read: {observation.get('first')}")
        print(f"  Second read: {observation.get('second')}")
        if observation.get("first") == observation.get("second"):
            print("  -> Snapshot stayed consistent under REPEATABLE READ.")
        else:
            print("  -> Snapshot changed unexpectedly.")
        self._set_anchor_price(100.0)

    def phantom_read_with_repeatable_read(self) -> None:
        print("\n[5] Phantom read attempt under REPEATABLE READ")
        seed_ids = self._seed_price_band([10.0, 20.0, 30.0], "Phantom Base")
        name_pattern = f"{self.DEMO_PREFIX} Phantom%"
        ready_for_insert = threading.Event()
        insert_done = threading.Event()
        observation: dict[str, Any] = {}

        def reader() -> None:
            conn = self._start_transaction("REPEATABLE READ")
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM items WHERE name LIKE %s AND deleted = false",
                        (name_pattern,),
                    )
                    observation["first"] = cur.fetchone()[0]
                ready_for_insert.set()
                insert_done.wait()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM items WHERE name LIKE %s AND deleted = false",
                        (name_pattern,),
                    )
                    observation["second"] = cur.fetchone()[0]
                conn.commit()
            finally:
                conn.close()

        def writer() -> None:
            ready_for_insert.wait()
            conn = self._start_transaction("READ COMMITTED")
            inserted_id: int | None = None
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO items (name, price, deleted)
                        VALUES (%s, %s, false)
                        RETURNING id
                        """,
                        (f"{self.DEMO_PREFIX} Phantom New", 50.0),
                    )
                    inserted_id = cur.fetchone()[0]
                conn.commit()
            finally:
                conn.close()
                if inserted_id is not None:
                    observation["inserted_id"] = inserted_id
            insert_done.set()

        threads = [threading.Thread(target=reader), threading.Thread(target=writer)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print(f"  First count: {observation.get('first')}")
        print(f"  Second count: {observation.get('second')}")
        if observation.get("first") != observation.get("second"):
            print("  -> Phantom read observed (range query saw new rows).")
        else:
            print(
                "  -> No phantom visible. PostgreSQL's REPEATABLE READ is snapshot-based, "
                "so inserts committed after the snapshot remain hidden."
            )

        extra_ids = seed_ids + [observation.get("inserted_id")]
        self._delete_items(extra_ids)

    def serializable_blocks_phantom(self) -> None:
        print("\n[6] Phantom protection with SERIALIZABLE")
        seed_ids = self._seed_price_band([5.0, 15.0, 25.0], "Serializable Base")
        name_pattern = f"{self.DEMO_PREFIX} Serializable%"
        ready_for_insert = threading.Event()
        insert_done = threading.Event()
        observation: dict[str, Any] = {}

        def reader() -> None:
            conn = self._start_transaction("SERIALIZABLE")
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM items WHERE name LIKE %s AND deleted = false",
                        (name_pattern,),
                    )
                    observation["first"] = cur.fetchone()[0]
                ready_for_insert.set()
                insert_done.wait()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM items WHERE name LIKE %s AND deleted = false",
                        (name_pattern,),
                    )
                    observation["second"] = cur.fetchone()[0]
                try:
                    conn.commit()
                except SerializationFailure as exc:
                    observation["serialization_failure"] = str(exc)
                    conn.rollback()
            finally:
                conn.close()

        def writer() -> None:
            ready_for_insert.wait()
            conn = self._start_transaction("READ COMMITTED")
            inserted_id: int | None = None
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO items (name, price, deleted)
                        VALUES (%s, %s, false)
                        RETURNING id
                        """,
                        (f"{self.DEMO_PREFIX} Serializable Extra", 12.0),
                    )
                    inserted_id = cur.fetchone()[0]
                conn.commit()
            finally:
                conn.close()
                if inserted_id is not None:
                    observation["inserted_id"] = inserted_id
            insert_done.set()

        threads = [threading.Thread(target=reader), threading.Thread(target=writer)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print(f"  First count: {observation.get('first')}")
        print(f"  Second count: {observation.get('second')}")
        if "serialization_failure" in observation:
            print(
                "  -> Concurrent write triggered SerializationFailure. PostgreSQL forced a retry "
                "instead of exposing a phantom row."
            )
        elif observation.get("first") == observation.get("second"):
            print("  -> Snapshot stayed stable; no phantoms under SERIALIZABLE.")
        else:
            print("  -> Phantom slipped through (unexpected for PostgreSQL).")

        extra_ids = seed_ids + [observation.get("inserted_id")]
        self._delete_items(extra_ids)

    def phantom_read_with_read_committed(self) -> None:
        print("\n[7] Phantom read under READ COMMITTED")
        seed_ids = self._seed_price_band([40.0, 45.0, 50.0], "Read Committed Base")
        name_pattern = f"{self.DEMO_PREFIX} Read Committed%"
        ready_for_insert = threading.Event()
        insert_done = threading.Event()
        observation: dict[str, Any] = {}

        def reader() -> None:
            conn = self._start_transaction("READ COMMITTED")
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM items WHERE name LIKE %s AND deleted = false",
                        (name_pattern,),
                    )
                    observation["first"] = cur.fetchone()[0]
                ready_for_insert.set()
                insert_done.wait()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM items WHERE name LIKE %s AND deleted = false",
                        (name_pattern,),
                    )
                    observation["second"] = cur.fetchone()[0]
                conn.commit()
            finally:
                conn.close()

        def writer() -> None:
            ready_for_insert.wait()
            conn = self._start_transaction("READ COMMITTED")
            inserted_id: int | None = None
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO items (name, price, deleted)
                        VALUES (%s, %s, false)
                        RETURNING id
                        """,
                        (f"{self.DEMO_PREFIX} Read Committed Extra", 42.0),
                    )
                    inserted_id = cur.fetchone()[0]
                conn.commit()
            finally:
                conn.close()
                if inserted_id is not None:
                    observation["inserted_id"] = inserted_id
            insert_done.set()

        threads = [threading.Thread(target=reader), threading.Thread(target=writer)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print(f"  First count: {observation.get('first')}")
        print(f"  Second count: {observation.get('second')}")
        if observation.get("first") != observation.get("second"):
            print("  -> Phantom read reproduced under READ COMMITTED.")
        else:
            print("  -> No phantom observed (try rerunning).")

        extra_ids = seed_ids + [observation.get("inserted_id")]
        self._delete_items(extra_ids)

    def run(self) -> None:
        self.dirty_read_with_read_uncommitted()
        self.clean_read_with_read_committed()
        self.non_repeatable_read_in_read_committed()
        self.repeatable_read_prevents_non_repeatable()
        self.phantom_read_with_repeatable_read()
        self.serializable_blocks_phantom()
        self.phantom_read_with_read_committed()


def main() -> None:
    demo = IsolationDemo()
    demo.run()


if __name__ == "__main__":
    main()
