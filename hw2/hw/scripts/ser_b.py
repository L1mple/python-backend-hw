from sqlalchemy import text
from scripts.common import engine

print("TX B: SERIALIZABLE")
with engine.connect() as conn:
    conn = conn.execution_options(isolation_level="SERIALIZABLE")
    trans = conn.begin()
    try:
        v1 = conn.execute(text("SELECT price FROM items WHERE name='demo-nrr'")).scalar_one()
        print("B: прочитал price =", v1)
        input("B: Нажми Enter для UPDATE (в A тоже нажми Enter)... ")

        conn.execute(text("UPDATE items SET price = price + 5 WHERE name='demo-nrr'"))
        trans.commit()
        print("B: COMMIT ok")
    except Exception as e:
        trans.rollback()
        print("B: ROLLBACK, ошибка:", e)
        raise
