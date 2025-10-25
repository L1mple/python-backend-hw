import sys, os, time
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

os.environ["DATABASE_URL"] = "postgresql+psycopg2://postgres:password@localhost:5433/shop_db"
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from service.main import ItemOrm, Base

# Database connection
DATABASE_URL = "postgresql+psycopg2://postgres:password@localhost:5433/shop_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def transaction_1():
    print("Transaction 1: Starting")
    db: Session = SessionLocal()
    try:
        db.begin()
        item = db.query(ItemOrm).filter_by(id=1).first()
        if not item:
            print("Transaction 1: Item not found, creating new one with price 150")
            item = ItemOrm(id=1, name="Apple", price=150.0, deleted=False)
            db.add(item)
            db.flush()
        else:
            print(f"Transaction 1: Item found, it's price = {item.price}")
        item.price = 200.0
        db.flush()
        print("Transaction 1: Changed price to 200 (not committed)")
        
        time.sleep(5)
        
        print("Transaction 1: Rolling back")
        db.rollback()
    except Exception as e:
        print(f"Transaction 1: Error - {e}")
        db.rollback()
    finally:
        db.close()

def transaction_2():
    # Wait for transaction 1 to change price
    time.sleep(2)
    
    print("Transaction 2: Starting")
    db: Session = SessionLocal()
    try:
        # Read item price in Read Committed
        db.begin()
        item = db.query(ItemOrm).filter_by(id=1).first()
        if item:
            print(f"Transaction 2: Read price = {item.price}")
        else:
            print("Transaction 2: No item found")
        db.commit()
    finally:
        db.close()

def run_dirty_read():
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

    print("\n===== DIRTY READ TEST =====")
    
    print("\n=== Test with Read Committed ===")
    print("(Read Uncommitted is not supported in Postgres where default isolation level is Read Committed)")

    t1 = threading.Thread(target=transaction_1)
    t2 = threading.Thread(target=transaction_2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

if __name__ == "__main__":
    run_dirty_read()