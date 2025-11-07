import threading
import time
from decimal import Decimal
from typing import Callable

from sqlalchemy import text, select, delete, func
from sqlalchemy.exc import OperationalError

from src.db import SessionLocal
from src.models import Item

def _print_header(title: str):
    print(f"\n===== {title} =====\n")

def _seed_item_fixed(id_: int = 1, name: str = "Apple", price: float = 150.0):
    db = SessionLocal()
    try:
        db.begin()
        db.execute(delete(Item).where(Item.id == id_))
        db.commit()
        print(f"Cleared item with id={id_}")

        db.begin()
        it = Item(id=id_, name=name, price=Decimal(str(price)), deleted=False)
        db.add(it)
        db.commit()
        print(f"Created item with id={id_} and price={price}")
    except Exception as e:
        print(f"Setup: Error - {e}")
        db.rollback()
    finally:
        db.close()

def _clear_prefix(prefix: str):
    db = SessionLocal()
    try:
        db.begin()
        db.execute(text("DELETE FROM items WHERE name LIKE :p"), {"p": f"{prefix}%"})
        db.commit()
        print(f"Cleared items with prefix {prefix}")
    finally:
        db.close()

def _seed_prefix(prefix: str, names_prices: list[tuple[str, float]]):
    db = SessionLocal()
    try:
        db.begin()
        for name, price in names_prices:
            db.add(Item(name=name, price=Decimal(str(price)), deleted=False))
        db.commit()
        print(f"Seeded items: {', '.join(n for n, _ in names_prices)}")
    finally:
        db.close()

def _with_tx(db, iso: str | None = None):
    db.begin()
    if iso:
        db.execute(text(f"SET TRANSACTION ISOLATION LEVEL {iso}"))
    return db


def test_dirty_read_like():
    _seed_item_fixed(id_=1, name="Apple", price=150.0)
    _print_header("DIRTY READ TEST")
    print("=== Test with Read Committed ===")
    print("(Read Uncommitted is not supported in Postgres; default is Read Committed)")

    def t1():
        print("Transaction 1: Starting")
        db = SessionLocal()
        try:
            _with_tx(db, "READ COMMITTED")
            item = db.get(Item, 1)
            if not item:
                print("Transaction 1: Item not found, creating with price 150")
                item = Item(id=1, name="Apple", price=Decimal("150.0"), deleted=False)
                db.add(item)
                db.flush()
            else:
                print(f"Transaction 1: Item found, its price = {item.price}")
            item.price = Decimal("200.0")
            db.flush()
            print("Transaction 1: Changed price to 200 (not committed)")
            time.sleep(5)
            print("Transaction 1: Rolling back")
            db.rollback()
        except Exception as e:
            print(f"Transaction 1: Error - {e}")
            db.rollback()
        finally:
            db.close()

    def t2():
        time.sleep(2)
        print("Transaction 2: Starting")
        db = SessionLocal()
        try:
            _with_tx(db, "READ COMMITTED")
            item = db.get(Item, 1)
            if item:
                print(f"Transaction 2: Read price = {item.price}")
            else:
                print("Transaction 2: No item found")
            db.commit()
        finally:
            db.close()

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start()
    th1.join(); th2.join()

def test_nonrepeatable_read_rc():
    _seed_item_fixed(id_=1, name="Apple", price=150.0)
    _print_header("NON-REPEATABLE READ TEST (READ COMMITTED)")

    def t1():
        print("T1: Starting (RC)")
        db = SessionLocal()
        try:
            _with_tx(db, "READ COMMITTED")
            v1 = db.get(Item, 1).price
            print(f"T1: First read = {v1}")
            time.sleep(3)
            v2 = db.get(Item, 1).price
            print(f"T1: Second read (changed) = {v2}")
            db.commit()
        finally:
            db.close()

    def t2():
        time.sleep(1)
        print("T2: Starting writer (RC)")
        db = SessionLocal()
        try:
            _with_tx(db, "READ COMMITTED")
            it = db.get(Item, 1)
            it.price = Decimal("250.0")
            db.flush()
            db.commit()
            print("T2: Committed update to 250")
        finally:
            db.close()

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start()
    th1.join(); th2.join()

def test_nonrepeatable_read_rr():
    _seed_item_fixed(id_=1, name="Apple", price=150.0)
    _print_header("NON-REPEATABLE READ PREVENTED (REPEATABLE READ)")

    def t1():
        print("T1: Starting (RR)")
        db = SessionLocal()
        try:
            _with_tx(db, "REPEATABLE READ")
            v1 = db.get(Item, 1).price
            print(f"T1: First read = {v1}")
            time.sleep(3)
            v2 = db.get(Item, 1).price
            print(f"T1: Second read (same snapshot) = {v2}")
            db.commit()
        finally:
            db.close()

    def t2():
        time.sleep(1)
        print("T2: Starting writer (RC)")
        db = SessionLocal()
        try:
            _with_tx(db, "READ COMMITTED")
            it = db.get(Item, 1)
            it.price = Decimal("300.0")
            db.commit()
            print("T2: Committed update to 300 (not visible to T1)")
        finally:
            db.close()

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start()
    th1.join(); th2.join()

def test_phantom_rc():
    prefix = "Z"
    _print_header("PHANTOM READ TEST (READ COMMITTED)")
    _clear_prefix(prefix)
    _seed_prefix(prefix, [(f"{prefix}1", 100.0)])

    def t1():
        print("T1: Starting (RC)")
        db = SessionLocal()
        try:
            _with_tx(db, "READ COMMITTED")
            cnt1 = db.execute(select(func.count()).select_from(Item).where(Item.name.like(f"{prefix}%"), Item.deleted.is_(False))).scalar_one()
            print(f"T1: First count = {cnt1}")
            time.sleep(3)
            cnt2 = db.execute(select(func.count()).select_from(Item).where(Item.name.like(f"{prefix}%"), Item.deleted.is_(False))).scalar_one()
            print(f"T1: Second count (phantom appeared) = {cnt2}")
            db.commit()
        finally:
            db.close()

    def t2():
        time.sleep(1)
        print("T2: Starting inserter (RC)")
        db = SessionLocal()
        try:
            _with_tx(db, "READ COMMITTED")
            db.add(Item(name=f"{prefix}2", price=Decimal("111.0"), deleted=False))
            db.commit()
            print(f"T2: Inserted {prefix}2")
        finally:
            db.close()

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start()
    th1.join(); th2.join()

def test_phantom_rr():
    prefix = "Z"
    _print_header("NO PHANTOM READ (REPEATABLE READ)")
    _clear_prefix(prefix)
    _seed_prefix(prefix, [(f"{prefix}1", 100.0)])

    def t1():
        print("T1: Starting (RR)")
        db = SessionLocal()
        try:
            _with_tx(db, "REPEATABLE READ")
            cnt1 = db.execute(select(func.count()).select_from(Item).where(Item.name.like(f"{prefix}%"), Item.deleted.is_(False))).scalar_one()
            print(f"T1: First count = {cnt1}")
            time.sleep(3)
            cnt2 = db.execute(select(func.count()).select_from(Item).where(Item.name.like(f"{prefix}%"), Item.deleted.is_(False))).scalar_one()
            print(f"T1: Second count (no phantom) = {cnt2}")
            db.commit()
        finally:
            db.close()

    def t2():
        time.sleep(1)
        print("T2: Starting inserter (RC)")
        db = SessionLocal()
        try:
            _with_tx(db, "READ COMMITTED")
            db.add(Item(name=f"{prefix}3", price=Decimal("123.0"), deleted=False))
            db.commit()
            print(f"T2: Inserted {prefix}3 (not visible to T1 snapshot)")
        finally:
            db.close()

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start()
    th1.join(); th2.join()

def test_serializable_no_phantom():
    prefix = "S"
    _print_header("NO PHANTOM READ (SERIALIZABLE)")
    _clear_prefix(prefix)
    _seed_prefix(prefix, [(f"{prefix}1", 100.0)])

    ser_fail = []

    def t1():
        print("T1: Starting (SERIALIZABLE)")
        db = SessionLocal()
        try:
            _with_tx(db, "SERIALIZABLE")
            cnt1 = db.execute(select(func.count()).select_from(Item).where(Item.name.like(f"{prefix}%"), Item.deleted.is_(False))).scalar_one()
            print(f"T1: First count = {cnt1}")
            time.sleep(3)
            cnt2 = db.execute(select(func.count()).select_from(Item).where(Item.name.like(f"{prefix}%"), Item.deleted.is_(False))).scalar_one()
            print(f"T1: Second count (no phantom) = {cnt2}")
            try:
                db.commit()
                print("T1: Commit OK")
            except OperationalError as e:
                ser_fail.append("T1")
                print(f"T1: Serialization failure: {e.__class__.__name__}")
                db.rollback()
        finally:
            db.close()

    def t2():
        time.sleep(1)
        print("T2: Starting inserter (SERIALIZABLE)")
        db = SessionLocal()
        try:
            _with_tx(db, "SERIALIZABLE")
            db.add(Item(name=f"{prefix}2", price=Decimal("222.0"), deleted=False))
            try:
                db.commit()
                print(f"T2: Commit OK ({prefix}2 inserted)")
            except OperationalError as e:
                ser_fail.append("T2")
                print(f"T2: Serialization failure: {e.__class__.__name__}")
                db.rollback()
        finally:
            db.close()

    th1 = threading.Thread(target=t1)
    th2 = threading.Thread(target=t2)
    th1.start(); th2.start()
    th1.join(); th2.join()


def main():
    print("Starting all isolation level tests...")

    test_dirty_read_like()
    test_nonrepeatable_read_rc()
    test_nonrepeatable_read_rr()
    test_phantom_rc()
    test_phantom_rr()
    test_serializable_no_phantom()

if __name__ == "__main__":
    main()
