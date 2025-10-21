from sqlalchemy import create_engine, text

engine = create_engine("postgresql+psycopg2://postgres:1234@localhost:5432/shop_db")

with engine.begin() as conn:
    conn.execute(text("""
    DROP TABLE IF EXISTS accounts;
    CREATE TABLE accounts (
        id SERIAL PRIMARY KEY,
        name TEXT,
        balance INT
    );
    INSERT INTO accounts (name, balance) VALUES ('Alice', 100), ('Bob', 200);
    """))
print("База тестирования успешно инициализирована.")
