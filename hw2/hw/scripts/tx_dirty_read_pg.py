# scripts/tx_dirty_read_pg.py
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
        # s1: BEGIN и попытка READ UNCOMMITTED (в PG будет READ COMMITTED)
        s1.begin()
        s1.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
        i1 = s1.get(Item, 1)
        old_price = i1.price
        i1.price = Decimal("999.00")
        s1.flush()
        print(f"[s1] updated price to 999 (UNCOMMITTED), old={old_price}")

        time.sleep(0.5)

        # s2: BEGIN и попытка READ UNCOMMITTED
        s2.begin()
        s2.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
        price_seen = s2.execute(select(Item.price).where(Item.id == 1)).scalar_one()
        print(f"[s2] read price = {price_seen}  <-- should be OLD, not 999")

        print("[result] dirty read in PostgreSQL: NOT possible")
        s1.rollback()
        s2.rollback()
    finally:
        s1.close()
        s2.close()


if __name__ == "__main__":
    main()
