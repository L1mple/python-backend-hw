# scripts/common.py
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://shop:shop@postgres:5432/shop",  # внутри docker
)

engine = create_engine(DATABASE_URL, future=True, echo=False)

def reset_items_to_known_state():
    # Подготовим фиксированные данные, чтобы сценарии были воспроизводимы
    with engine.begin() as conn:
        conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS items (
              id SERIAL PRIMARY KEY,
              name TEXT NOT NULL,
              price DOUBLE PRECISION NOT NULL CHECK (price >= 0),
              deleted BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)
        # Чистим "тестовые" записи
        conn.execute(text("DELETE FROM items WHERE name LIKE 'demo-%'"))
        # Вставляем демо-строки
        conn.execute(text("INSERT INTO items (name, price, deleted) VALUES "
                          "('demo-nrr', 100, false), "
                          "('demo-phantom-1', 50, false)"))
        # Убедимся, что есть хотя бы одна >100 для фантому
        conn.execute(text("INSERT INTO items (name, price, deleted) "
                          "SELECT 'demo-phantom-2', 150, false "
                          "WHERE NOT EXISTS (SELECT 1 FROM items WHERE price > 100)"))
