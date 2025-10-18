# scripts/seed.py
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text

from shop_api.db import session_scope
from shop_api.orm import Item, Cart


def main():
    print("[seed] truncating tables (RESTART IDENTITY)...")
    with session_scope() as db:
        # Сброс данных и последовательностей
        db.execute(text("TRUNCATE TABLE cart_items, carts, items RESTART IDENTITY CASCADE"))

        # базовые данные
        pen = Item(name="Pen", price=Decimal("100.00"), deleted=False)         # станет id=1
        notebook = Item(name="Notebook", price=Decimal("60.00"), deleted=False)  # id=2
        old = Item(name="Old", price=Decimal("15.00"), deleted=True)             # id=3
        db.add_all([pen, notebook, old])
        db.flush()

        cart = Cart()  # id=1
        db.add(cart)
        db.flush()

        print(f"[seed] items: {[pen.id, notebook.id, old.id]}, cart: {cart.id}")
        print("[seed] done.")


if __name__ == "__main__":
    main()
