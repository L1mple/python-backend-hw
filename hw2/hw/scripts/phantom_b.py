from sqlalchemy import text
from scripts.common import engine

print("TX B: INSERT новой строки (price=200) + COMMIT")
with engine.begin() as conn:
    conn.execute(text("INSERT INTO items (name, price, deleted) VALUES ('demo-phantom-new', 200, false)"))
    c = conn.execute(text("SELECT COUNT(*) FROM items WHERE price > 100")).scalar_one()
    print("B: COUNT(price>100) теперь =", c)
