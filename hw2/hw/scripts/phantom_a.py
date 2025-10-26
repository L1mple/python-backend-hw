from sqlalchemy import text
from scripts.common import engine, reset_items_to_known_state

reset_items_to_known_state()

print("TX A: READ COMMITTED (по умолчанию)")
with engine.connect() as conn:
    trans = conn.begin()
    try:
        c1 = conn.execute(text("SELECT COUNT(*) FROM items WHERE price > 100")).scalar_one()
        print("A: 1-й COUNT(price>100) =", c1)
        input("A: Пауза. Запусти phantom_b.py в другом окне, затем Enter здесь... ")

        c2 = conn.execute(text("SELECT COUNT(*) FROM items WHERE price > 100")).scalar_one()
        print("A: 2-й COUNT(price>100) =", c2, "(ожидаем БОЛЬШЕ в READ COMMITTED)")
        trans.commit()
    except:
        trans.rollback()
        raise
