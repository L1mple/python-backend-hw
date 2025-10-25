# scripts/tx_nonrepeat_rc.py
from __future__ import annotations

import time
from decimal import Decimal

from sqlalchemy import text, select
from sqlalchemy.orm import Session

from shop_api.db import SessionLocal
from shop_api.orm import Item


def main():
    s1: Session = SessionLocal()
    s2: Session = SessionLocal()
    try:
        # s1: READ COMMITTED
        s1.begin()
        s1.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        v1 = s1.execute(select(Item.price).where(Item.id == 1)).scalar_one()
        print(f"[s1] first read price = {v1}")

        time.sleep(0.5)

        # s2: меняет значение и коммитит
        s2.begin()
        s2.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        i1 = s2.get(Item, 1)
        i1.price = Decimal("200.00")
        s2.flush()
        s2.commit()
        print("[s2] update+commit -> price = 200.00")

        time.sleep(0.5)

        # s1: повторное чтение в той же транзакции
        v2 = s1.execute(select(Item.price).where(Item.id == 1)).scalar_one()
        print(f"[s1] second read price = {v2}  <-- changed within same tx")

        print("[result] non-repeatable read observed on READ COMMITTED")
        s1.commit()
    finally:
        s1.close()
        s2.close()


if __name__ == "__main__":
    main()
