# scripts/nrr_a.py
from scripts.common import engine, reset_items_to_known_state
from sqlalchemy import text

reset_items_to_known_state()

print("TX A: READ COMMITTED (по умолчанию)")
with engine.connect() as conn:
    # уровень по умолчанию READ COMMITTED
    trans = conn.begin()
    try:
        v1 = conn.execute(text("SELECT price FROM items WHERE name='demo-nrr'")).scalar_one()
        print("A: 1-й SELECT price =", v1)
        input("A: Пауза. Теперь запусти nrr_b.py в другом терминале и жми Enter здесь... ")

        v2 = conn.execute(text("SELECT price FROM items WHERE name='demo-nrr'")).scalar_one()
        print("A: 2-й SELECT price =", v2)
        trans.commit()
    except:
        trans.rollback()
        raise
