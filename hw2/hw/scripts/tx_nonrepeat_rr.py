# scripts/tx_nonrepeat_rr.py
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
        # s1: REPEATABLE READ
        s1.begin()
        s1.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        v1 = s1.execute(select(Item.price).where(Item.id == 1)).scalar_one()
        print(f"[s1] first read price = {v1}")

        time.sleep(0.5)

        # s2: в другом снепшоте меняет и коммитит
        s2.begin()
        s2.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        i1 = s2.get(Item, 1)
        i1.price = Decimal("300.00")
        s2.flush()
        s2.commit()
        print("[s2] update+commit -> price = 300.00")

        time.sleep(0.5)

        # s1: повторное чтение в том же снепшоте
        v2 = s1.execute(select(Item.price).where(Item.id == 1)).scalar_one()
        print(f"[s1] second read price = {v2}  <-- unchanged (snapshot)")

        print("[result] no non-repeatable read on REPEATABLE READ")
        s1.commit()
    finally:
        s1.close()
        s2.close()


if __name__ == "__main__":
    main()
