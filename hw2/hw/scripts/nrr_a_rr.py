from sqlalchemy import text
from scripts.common import engine, reset_items_to_known_state

reset_items_to_known_state()

print("TX A: REPEATABLE READ")
with engine.connect() as conn:
    conn = conn.execution_options(isolation_level="REPEATABLE READ")
    trans = conn.begin()
    try:
        v1 = conn.execute(text("SELECT price FROM items WHERE name='demo-nrr'")).scalar_one()
        print("A: 1-й SELECT price =", v1)
        input("A: Пауза. Запусти nrr_b.py в другом окне, затем Enter здесь... ")

        v2 = conn.execute(text("SELECT price FROM items WHERE name='demo-nrr'")).scalar_one()
        print("A: 2-й SELECT price =", v2, "(ожидаем тот же, что и v1)")
        trans.commit()
    except:
        trans.rollback()
        raise
