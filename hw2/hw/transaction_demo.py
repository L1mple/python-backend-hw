import asyncio
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import time

DATABASE_URL = "sqlite:///./shop.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)

def setup_database():
    """Создаем тестовые данные"""
    session = SessionLocal()
    try:
        # Включаем WAL mode для лучшей параллельной работы
        session.execute(text("PRAGMA journal_mode=WAL"))
        
        # Создаем таблицы если их нет
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                deleted BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Очищаем и добавляем тестовые данные
        session.execute(text("DELETE FROM items"))
        session.execute(text("INSERT INTO items (name, price) VALUES ('Test Item', 10.0)"))
        session.commit()
        print("Database setup completed")
    finally:
        session.close()

def no_dirty_read_demo():
    """Демонстрация что SQLite предотвращает Dirty Reads"""
    print("\n=== No Dirty Read in SQLite ===")
    
    def transaction1():
        session = SessionLocal()
        try:
            session.execute(text("UPDATE items SET price = 2000.0 WHERE id = 1"))
            print("Transaction 1: Updated price to 2000 (not committed)")
            time.sleep(2)
            session.rollback()
            print("Transaction 1: Rolled back")
        finally:
            session.close()

    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(1)
            result = session.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()
            print(f"Transaction 2: Read price = {result[0]} (cannot see uncommitted changes)")
        finally:
            session.close()

    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

def non_repeatable_read_demo():
    """Демонстрация Non-Repeatable Read в SQLite"""
    print("\n=== Non-Repeatable Read Demo ===")
    
    def transaction1():
        session = SessionLocal()
        try:
            result = session.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()
            print(f"Transaction 1: First read price = {result[0]}")
            time.sleep(2)
            result = session.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()
            print(f"Transaction 1: Second read price = {result[0]} (changed!)")
        finally:
            session.close()

    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(1)
            session.execute(text("UPDATE items SET price = price + 100 WHERE id = 1"))
            session.commit()
            print("Transaction 2: Updated price and committed")
        finally:
            session.close()

    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

def phantom_read_demo():
    """Демонстрация Phantom Read в SQLite"""
    print("\n=== Phantom Read Demo ===")
    
    def transaction1():
        session = SessionLocal()
        try:
            count = session.execute(text("SELECT COUNT(*) FROM items WHERE price > 50")).scalar()
            print(f"Transaction 1: First count = {count}")
            time.sleep(2)
            count = session.execute(text("SELECT COUNT(*) FROM items WHERE price > 50")).scalar()
            print(f"Transaction 1: Second count = {count} (phantom read!)")
        finally:
            session.close()

    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(1)
            session.execute(text("INSERT INTO items (name, price) VALUES ('New Item', 100)"))
            session.commit()
            print("Transaction 2: Inserted new item with price 100")
        finally:
            session.close()

    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

def serializable_demo():
    """Демонстрация SERIALIZABLE в SQLite"""
    print("\n=== Serializable Isolation Demo ===")
    
    def transaction1():
        session = SessionLocal()
        try:
            # SERIALIZABLE в SQLite - дефолтный режим при EXCLUSIVE lock
            session.execute(text("BEGIN EXCLUSIVE"))
            count = session.execute(text("SELECT COUNT(*) FROM items")).scalar()
            print(f"Transaction 1: Count = {count}")
            time.sleep(2)
            session.execute(text("INSERT INTO items (name, price) VALUES ('Item from T1', 50)"))
            session.commit()
            print("Transaction 1: Committed")
        except Exception as e:
            print(f"Transaction 1: Error - {e}")
            session.rollback()
        finally:
            session.close()

    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(1)
            # Будет ждать пока T1 завершится
            session.execute(text("BEGIN EXCLUSIVE"))
            session.execute(text("INSERT INTO items (name, price) VALUES ('Item from T2', 60)"))
            session.commit()
            print("Transaction 2: Committed after waiting")
        except Exception as e:
            print(f"Transaction 2: Error - {e}")
            session.rollback()
        finally:
            session.close()

    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

if __name__ == "__main__":
    setup_database()
    
    print("=== SQLite Transaction Isolation Demo ===")
    print("Note: SQLite has fixed isolation levels")
    print("Default: READ COMMITTED (prevents dirty reads)")
    
    no_dirty_read_demo()
    non_repeatable_read_demo()
    phantom_read_demo()
    serializable_demo()