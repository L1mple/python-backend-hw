import sys, os, time
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import text

os.environ["DATABASE_URL"] = "postgresql+psycopg2://postgres:password@localhost:5433/shop_db"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from service.main import ItemOrm, Base

# Database connection
DATABASE_URL = "postgresql+psycopg2://postgres:password@localhost:5433/shop_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def transaction_1(isolation_level: str):
    print(f"Transaction 1: Starting with {isolation_level}")
    db: Session = SessionLocal()
    try:
        db.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
        item = db.query(ItemOrm).filter_by(id=1).first()
        if not item:
            print("Transaction 1: Item not found, creating new one with price 150")
            item = ItemOrm(id=1, name="Apple", price=150.0, deleted=False)
            db.add(item)
            db.flush()
        print(f"Transaction 1: First read, price = {item.price}")
        
        time.sleep(5)
        
        db.expire(item)
        item = db.query(ItemOrm).filter_by(id=1).first()
        print(f"Transaction 1: Second read, price = {item.price}")
        db.commit()
    except Exception as e:
        print(f"Transaction 1: Error - {e}")
        db.rollback()
    finally:
        db.close()

def transaction_2():
    # Wait for transaction 1 to do first read
    time.sleep(2)
    
    print("Transaction 2: Starting")
    db: Session = SessionLocal()
    try:
        db.begin()
        item = db.query(ItemOrm).filter_by(id=1).first()
        if item:
            item.price = 200.0
            db.commit()
            print("Transaction 2: Changed price to 200 and committed")
        else:
            print("Transaction 2: No item found")
    except Exception as e:
        print(f"Transaction 2: Error - {e}")
        db.rollback()
    finally:
        db.close()

def run_non_repeatable_read():
    db = SessionLocal()
    try:
        db.query(ItemOrm).filter(ItemOrm.id == 1).delete()
        db.commit()
        print("\nCleared item with id=1")
        
        item = ItemOrm(id=1, name="Apple", price=150.0, deleted=False)
        db.add(item)
        db.commit()
        print("Created item with id=1 and price=150.0")
    except Exception as e:
        print(f"Setup: Error - {e}")
        db.rollback()
    finally:
        db.close()

    Base.metadata.create_all(bind=engine)

    print("\n===== NON-REPEATABLE READ TEST =====")

    print("\n=== Test with Read Committed (should show non-repeatable read) ===")
    t1 = threading.Thread(target=transaction_1, args=("READ COMMITTED",))
    t2 = threading.Thread(target=transaction_2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Reset price to 150
    db = SessionLocal()
    try:
        item = db.query(ItemOrm).filter_by(id=1).first()
        item.price = 150.0
        db.commit()
        print("\nReset price to 150.0")
    except Exception as e:
        print(f"Reset: Error - {e}")
        db.rollback()
    finally:
        db.close()

    print("\n=== Test with Repeatable Read (should not show non-repeatable read) ===")
    t1 = threading.Thread(target=transaction_1, args=("REPEATABLE READ",))
    t2 = threading.Thread(target=transaction_2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

if __name__ == "__main__":
    run_non_repeatable_read()