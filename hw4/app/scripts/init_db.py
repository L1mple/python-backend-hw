from sqlalchemy import text
from src.db import engine
from src.models import Base

def main():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO items (name, price, deleted) VALUES ('A1', 100, false), ('B1', 200, false)"))

if __name__ == "__main__":
    main()
