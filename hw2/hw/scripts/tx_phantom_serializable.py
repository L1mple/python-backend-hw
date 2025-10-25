# scripts/tx_phantom_serializable.py
from __future__ import annotations

import threading
import time
from decimal import Decimal

from sqlalchemy import text, select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from shop_api.db import SessionLocal
from shop_api.orm import Item

TARGET_NAME = "SERIAL_GUARD"

def worker(name: str, first_event: threading.Event, second_event: threading.Event):
    """
    Транзакция SERIALIZABLE: если записей с TARGET_NAME нет — вставить одну.
    Барьер синхронизации используем ТОЛЬКО на первой попытке, чтобы гарантированно
    смоделировать конфликт. На ретраях барьер пропускаем, иначе можно подвиснуть,
    если другая транзакция уже завершилась.
    """
    attempt = 1
    while True:
        s: Session = SessionLocal()
        try:
            s.begin()
            s.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            cnt = s.execute(
                select(func.count()).select_from(Item).where(Item.name == TARGET_NAME)
            ).scalar_one()
            print(f"[{name}] attempt {attempt}: count({TARGET_NAME}) = {cnt}")

            # Барьер — только на первом заходе
            if attempt == 1:
                if name == "T1":
                    first_event.set()
                    second_event.wait(timeout=2.0)  # на всякий случай таймаут
                else:
                    second_event.set()
                    first_event.wait(timeout=2.0)

            if cnt == 0:
                s.add(Item(name=TARGET_NAME, price=Decimal("1.00"), deleted=False))
                s.flush()
                print(f"[{name}] inserting {TARGET_NAME}...")

            time.sleep(0.2)  # чуть-чуть, чтобы коммиты пересеклись на 1-й попытке
            s.commit()
            print(f"[{name}] commit OK")
            break
        except OperationalError as e:
            # 40001 — ошибка сериализации: повторяем без барьера
            print(f"[{name}] commit failed (serialization), retrying... ({e})")
            s.rollback()
            attempt += 1
            time.sleep(0.3)
        finally:
            s.close()

def cleanup():
    s = SessionLocal()
    try:
        s.begin()
        s.execute(text(f"DELETE FROM items WHERE name = :n"), {"n": TARGET_NAME})
        s.commit()
    finally:
        s.close()

def main():
    print("[serializable] cleanup...")
    cleanup()

    e1 = threading.Event()
    e2 = threading.Event()

    t1 = threading.Thread(target=worker, args=("T1", e1, e2), daemon=True)
    t2 = threading.Thread(target=worker, args=("T2", e1, e2), daemon=True)

    t1.start()
    t2.start()

    # На всякий случай не ждём бесконечно
    t1.join(timeout=10)
    t2.join(timeout=10)

    if t1.is_alive() or t2.is_alive():
        print("[warn] some worker still running (timed out join), but DB state should be consistent.")

    s = SessionLocal()
    try:
        total = s.execute(
            select(func.count()).select_from(Item).where(Item.name == TARGET_NAME)
        ).scalar_one()
        print(f"[result] rows with name={TARGET_NAME}: {total} (should be 1)")
    finally:
        s.close()

if __name__ == "__main__":
    main()
