import threading
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DB_URL = "postgresql://stepa_user:stepa_password@localhost:5433/stepa_shop_db"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

def demonstrate_read_committed_behavior():
    print("READ COMMITTED: Non-repeatable Read Example")
    
    def read_transaction():
        session = SessionLocal()
        try:
            session.execute(text("BEGIN"))
            
            first_read = session.execute(text("SELECT cost FROM products WHERE id = 2")).fetchone()
            print(f"First read - Product 2 cost: {first_read[0]}")
            
            time.sleep(2)
            
            second_read = session.execute(text("SELECT cost FROM products WHERE id = 2")).fetchone()
            print(f"Second read - Product 2 cost: {second_read[0]}")
            
            if first_read[0] != second_read[0]:
                print("NON-REPEATABLE READ DETECTED: Cost changed during transaction")
            else:
                print("No change detected")
                
            session.execute(text("COMMIT"))
        except Exception as error:
            print(f"Read transaction error: {error}")
            session.execute(text("ROLLBACK"))
        finally:
            session.close()

    def write_transaction():
        session = SessionLocal()
        try:
            time.sleep(1)
            print("Updating product cost...")
            session.execute(text("UPDATE products SET cost = cost + 50 WHERE id = 2"))
            session.commit()
            print("Update committed successfully")
        except Exception as error:
            print(f"Write transaction error: {error}")
        finally:
            session.close()

    reader = threading.Thread(target=read_transaction)
    writer = threading.Thread(target=write_transaction)
    
    reader.start()
    writer.start()
    
    reader.join()
    writer.join()

def demonstrate_repeatable_read_behavior():
    print("\nREPEATABLE READ: Consistent Read Example")
    
    def read_transaction():
        session = SessionLocal()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            session.execute(text("BEGIN"))
            
            first_read = session.execute(text("SELECT cost FROM products WHERE id = 3")).fetchone()
            print(f"First read - Product 3 cost: {first_read[0]}")
            
            time.sleep(2)
            
            second_read = session.execute(text("SELECT cost FROM products WHERE id = 3")).fetchone()
            print(f"Second read - Product 3 cost: {second_read[0]}")
            
            if first_read[0] != second_read[0]:
                print("UNEXPECTED: Cost changed in REPEATABLE READ")
            else:
                print("CONSISTENT: Same cost in both reads")
                
            session.execute(text("COMMIT"))
        except Exception as error:
            print(f"Read transaction error: {error}")
            session.execute(text("ROLLBACK"))
        finally:
            session.close()

    def write_transaction():
        session = SessionLocal()
        try:
            time.sleep(1)
            print("Modifying product cost...")
            session.execute(text("UPDATE products SET cost = cost + 30 WHERE id = 3"))
            session.commit()
            print("Modification committed")
        except Exception as error:
            print(f"Write transaction error: {error}")
        finally:
            session.close()

    reader = threading.Thread(target=read_transaction)
    writer = threading.Thread(target=write_transaction)
    
    reader.start()
    writer.start()
    
    reader.join()
    writer.join()

if __name__ == "__main__":
    print("Testing PostgreSQL Transaction Isolation Levels")
    print("=" * 55)
    
    demonstrate_read_committed_behavior()
    demonstrate_repeatable_read_behavior()
    
    print("\n" + "=" * 55)
    print("Isolation level testing completed")
