from sqlalchemy import text
from scripts.common import engine, reset_items_to_known_state

reset_items_to_known_state()

print("TX A: SERIALIZABLE")
with engine.connect() as conn:
    conn = conn.execution_options(isolation_level="SERIALIZABLE")
    trans = conn.begin()
    try:
        v1 = conn.execute(text("SELECT price FROM items WHERE name='demo-nrr'")).scalar_one()
        print("A: прочитал price =", v1)
        input("A: Пауза. Запусти ser_b.py и затем Enter здесь для UPDATE... ")

        conn.execute(text("UPDATE items SET price = price + 10 WHERE name='demo-nrr'"))
        trans.commit()
        print("A: COMMIT ok")
    except Exception as e:
        trans.rollback()
        print("A: ROLLBACK, ошибка:", e)
        raise
