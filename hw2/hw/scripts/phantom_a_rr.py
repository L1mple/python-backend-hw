from sqlalchemy import text
from scripts.common import engine, reset_items_to_known_state

reset_items_to_known_state()

print("TX A: REPEATABLE READ")
with engine.connect() as conn:
    conn = conn.execution_options(isolation_level="REPEATABLE READ")
    trans = conn.begin()
    try:
        c1 = conn.execute(text("SELECT COUNT(*) FROM items WHERE price > 100")).scalar_one()
        print("A: 1-й COUNT(price>100) =", c1)
        input("A: Пауза. Запусти phantom_b.py, затем Enter здесь... ")

        c2 = conn.execute(text("SELECT COUNT(*) FROM items WHERE price > 100")).scalar_one()
        print("A: 2-й COUNT(price>100) =", c2, "(ожидаем такой же, как c1)")
        trans.commit()
    except:
        trans.rollback()
        raise
