# scripts/nrr_b.py
from scripts.common import engine
from sqlalchemy import text

print("TX B: меняем цену и коммитим")
with engine.begin() as conn:  # begin = BEGIN; COMMIT автоматически
    conn.execute(text("UPDATE items SET price = price + 20 WHERE name='demo-nrr'"))
    v = conn.execute(text("SELECT price FROM items WHERE name='demo-nrr'")).scalar_one()
    print("B: после UPDATE price =", v)
