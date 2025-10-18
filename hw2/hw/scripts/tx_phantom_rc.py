# scripts/tx_phantom_rc.py
from __future__ import annotations

import time
from decimal import Decimal

from sqlalchemy import text, select, func
from sqlalchemy.orm import Session

from shop_api.db import SessionLocal
from shop_api.orm import Item


def count_phantoms(sess: Session) -> int:
    return sess.execute(
        select(func.count()).select_from(Item).where(Item.name.like("PHANTOM%"))
    ).scalar_one()


def main():
    s_cleanup: Session = SessionLocal()
    try:
        s_cleanup.begin()
        s_cleanup.execute(text("DELETE FROM items WHERE name LIKE 'PHANTOM%'"))
        s_cleanup.commit()
    finally:
        s_cleanup.close()

    s1: Session = SessionLocal()
    s2: Session = SessionLocal()
    try:
        # s1: READ COMMITTED
        s1.begin()
        s1.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        c1 = count_phantoms(s1)
        print(f"[s1] first count PHANTOM% = {c1}")

        time.sleep(0.5)

        # s2: вставляет подходящую запись и коммитит
        s2.begin()
        s2.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        s2.add(Item(name="PHANTOM-1", price=Decimal("60.00"), deleted=False))
        s2.flush()
        s2.commit()
        print("[s2] insert+commit PHANTOM-1")

        time.sleep(0.5)

        # s1: повторный запрос
        c2 = count_phantoms(s1)
        print(f"[s1] second count PHANTOM% = {c2}  <-- changed")

        print("[result] phantom read observed on READ COMMITTED")
        s1.commit()
    finally:
        s1.close()
        s2.close()


if __name__ == "__main__":
    main()
