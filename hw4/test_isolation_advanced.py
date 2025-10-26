import threading
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://user:password@localhost:5432/shop_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def test_postgresql_isolation_behavior():
    """Демонстрация реального поведения изоляции в PostgreSQL"""
    print("=== PostgreSQL Isolation Levels Behavior ===")
    print("Note: PostgreSQL doesn't support true READ UNCOMMITTED")
    print("It upgrades READ UNCOMMITTED to READ COMMITTED")
    print()

def test_read_committed_non_repeatable():
    """Демонстрация Non-repeatable Read в READ COMMITTED"""
    print("=== READ COMMITTED: Non-repeatable Read ===")
    
    def reader():
        session = SessionLocal()
        try:
            # READ COMMITTED (default in PostgreSQL)
            session.execute(text("BEGIN"))
            
            # Первое чтение
            result1 = session.execute(text("SELECT price FROM items WHERE id = 3")).fetchone()
            print(f"Reader - First read (id=3): price = {result1[0]}")
            
            time.sleep(2)  # Ждем изменения
            
            # Второе чтение - может увидеть изменения других транзакций
            result2 = session.execute(text("SELECT price FROM items WHERE id = 3")).fetchone()
            print(f"Reader - Second read (id=3): price = {result2[0]}")
            
            if result1[0] != result2[0]:
                print("✅ NON-REPEATABLE READ: Price changed during transaction!")
            else:
                print("❌ No change detected")
                
            session.execute(text("COMMIT"))
        except Exception as e:
            print(f"Reader error: {e}")
            session.execute(text("ROLLBACK"))
        finally:
            session.close()

    def writer():
        session = SessionLocal()
        try:
            time.sleep(1)  # Даем время reader'у начать
            print("Writer: Updating price of item 3...")
            session.execute(text("UPDATE items SET price = price + 15 WHERE id = 3"))
            session.commit()
            print("Writer: Update committed")
        except Exception as e:
            print(f"Writer error: {e}")
        finally:
            session.close()

    t1 = threading.Thread(target=reader)
    t2 = threading.Thread(target=writer)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

def test_repeatable_read_consistency():
    """Демонстрация консистентности в REPEATABLE READ"""
    print("\n=== REPEATABLE READ: Consistent Reads ===")
    
    def reader():
        session = SessionLocal()
        try:
            # REPEATABLE READ - видит snapshot на начало транзакции
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            session.execute(text("BEGIN"))
            
            # Первое чтение
            result1 = session.execute(text("SELECT price FROM items WHERE id = 4")).fetchone()
            print(f"Reader - First read (id=4): price = {result1[0]}")
            
            time.sleep(2)  # Ждем изменения
            
            # Второе чтение - должно быть таким же благодаря snapshot
            result2 = session.execute(text("SELECT price FROM items WHERE id = 4")).fetchone()
            print(f"Reader - Second read (id=4): price = {result2[0]}")
            
            if result1[0] != result2[0]:
                print("❌ NON-REPEATABLE READ detected (unexpected in REPEATABLE READ)")
            else:
                print("✅ CONSISTENT: Same price in both reads (snapshot isolation)")
                
            session.execute(text("COMMIT"))
        except Exception as e:
            print(f"Reader error: {e}")
            session.execute(text("ROLLBACK"))
        finally:
            session.close()

    def writer():
        session = SessionLocal()
        try:
            time.sleep(1)
            print("Writer: Updating price of item 4...")
            session.execute(text("UPDATE items SET price = price + 20 WHERE id = 4"))
            session.commit()
            print("Writer: Update committed")
        except Exception as e:
            print(f"Writer error: {e}")
        finally:
            session.close()

    t1 = threading.Thread(target=reader)
    t2 = threading.Thread(target=writer)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

def test_serializable_conflict():
    """Демонстрация конфликтов в SERIALIZABLE"""
    print("\n=== SERIALIZABLE: Conflict Detection ===")
    
    def transaction1():
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            session.execute(text("BEGIN"))
            
            print("Transaction 1: Reading items...")
            result = session.execute(text("SELECT COUNT(*) FROM items")).fetchone()
            print(f"Transaction 1: Count = {result[0]}")
            
            time.sleep(2)
            
            print("Transaction 1: Trying to insert...")
            session.execute(text("INSERT INTO items (name, price) VALUES ('Serializable Test', 100.0)"))
            session.execute(text("COMMIT"))
            print("Transaction 1: Committed successfully")
            
        except Exception as e:
            print(f"Transaction 1 failed: {e}")
            session.execute(text("ROLLBACK"))
        finally:
            session.close()

    def transaction2():
        session = SessionLocal()
        try:
            time.sleep(1)
            session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            session.execute(text("BEGIN"))
            
            print("Transaction 2: Reading items...")
            result = session.execute(text("SELECT COUNT(*) FROM items")).fetchone()
            print(f"Transaction 2: Count = {result[0]}")
            
            print("Transaction 2: Trying to insert...")
            session.execute(text("INSERT INTO items (name, price) VALUES ('Serializable Test 2', 200.0)"))
            session.execute(text("COMMIT"))
            print("Transaction 2: Committed successfully")
            
        except Exception as e:
            print(f"Transaction 2 failed: {e}")
            session.execute(text("ROLLBACK"))
        finally:
            session.close()

    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

if __name__ == "__main__":
    test_postgresql_isolation_behavior()
    test_read_committed_non_repeatable()
    test_repeatable_read_consistency()
    test_serializable_conflict()
    
    print("\n" + "=" * 50)
    print("Advanced testing completed!")
    print("\nSummary:")
    print("- READ COMMITTED: Allows non-repeatable reads")
    print("- REPEATABLE READ: Prevents non-repeatable reads (snapshot)")
    print("- SERIALIZABLE: Detects serialization conflicts")
    print("- PostgreSQL doesn't implement true READ UNCOMMITTED")
