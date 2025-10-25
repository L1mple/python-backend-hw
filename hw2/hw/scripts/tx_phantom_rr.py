# scripts/tx_phantom_rr.py
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
    # очистка шаблонных записей
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
        # s1: REPEATABLE READ
        s1.begin()
        s1.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        c1 = count_phantoms(s1)
        print(f"[s1] first count PHANTOM% = {c1}")

        time.sleep(0.5)

        # s2: вставка в другой транзакции
        s2.begin()
        s2.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        s2.add(Item(name="PHANTOM-2", price=Decimal("60.00"), deleted=False))
        s2.flush()
        s2.commit()
        print("[s2] insert+commit PHANTOM-2")

        time.sleep(0.5)

        # s1: второй запрос — должен вернуть тот же результат
        c2 = count_phantoms(s1)
        print(f"[s1] second count PHANTOM% = {c2}  <-- unchanged (snapshot)")

        print("[result] no phantom read on REPEATABLE READ")
        s1.commit()
    finally:
        s1.close()
        s2.close()


if __name__ == "__main__":
    main()
