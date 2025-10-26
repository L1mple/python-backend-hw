from sqlalchemy import create_engine, text

# Подключение напрямую к PostgreSQL
engine = create_engine("postgresql+psycopg2://postgres:postgres@localhost:5432/shop", echo=True, future=True)

# --- Dirty Read (READ UNCOMMITTED) ---
with engine.connect() as conn1, engine.connect() as conn2:
    conn1.execute(text("BEGIN"))
    conn1.execute(text("UPDATE items SET price = price + 100 WHERE id = 1"))

    conn2.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
    result = conn2.execute(text("SELECT price FROM items WHERE id = 1")).scalar()
    print("Dirty read price:", result)

    conn1.rollback()
