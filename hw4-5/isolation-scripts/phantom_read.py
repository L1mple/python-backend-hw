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
        items = db.query(ItemOrm).filter(ItemOrm.price > 100).all()
        print(f"Transaction 1: First read, items = {[item.id for item in items]}")
        
        time.sleep(5)
        
        db.expire_all()
        items = db.query(ItemOrm).filter(ItemOrm.price > 100).all()
        print(f"Transaction 1: Second read, items = {[item.id for item in items]}")
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
        item = ItemOrm(id=2, name="Orange", price=200.0, deleted=False)
        db.add(item)
        db.commit()
        print("Transaction 2: Added item with id=2 and price=200")
    except Exception as e:
        print(f"Transaction 2: Error - {e}")
        db.rollback()
    finally:
        db.close()

def run_phantom_read():
    db = SessionLocal()
    try:
        db.query(ItemOrm).filter(ItemOrm.id.in_([1, 2])).delete()
        db.commit()
        print("\nCleared items with id=1 and id=2")
        
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

    print("\n===== PHANTOM READ TEST =====")

    print("\n=== Test with Read Committed (should show phantom read) ===")
    t1 = threading.Thread(target=transaction_1, args=("READ COMMITTED",))
    t2 = threading.Thread(target=transaction_2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Reset database
    db = SessionLocal()
    try:
        db.query(ItemOrm).filter(ItemOrm.id.in_([1, 2])).delete()
        db.commit()
        print("\nCleared items with id=1 and id=2")
        
        item = ItemOrm(id=1, name="Apple", price=150.0, deleted=False)
        db.add(item)
        db.commit()
        print("Created item with id=1 and price=150.0")
    except Exception as e:
        print(f"Reset: Error - {e}")
        db.rollback()
    finally:
        db.close()

    print("\n=== Test with Repeatable Read (should show phantom read) ===")
    print("(But Postgres realizes snapshot isolation which eliminated phantom read in most cases)")
    t1 = threading.Thread(target=transaction_1, args=("REPEATABLE READ",))
    t2 = threading.Thread(target=transaction_2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Reset database
    db = SessionLocal()
    try:
        db.query(ItemOrm).filter(ItemOrm.id.in_([1, 2])).delete()
        db.commit()
        print("\nCleared items with id=1 and id=2")
        
        item = ItemOrm(id=1, name="Apple", price=150.0, deleted=False)
        db.add(item)
        db.commit()
        print("Created item with id=1 and price=150.0")
    except Exception as e:
        print(f"Reset: Error - {e}")
        db.rollback()
    finally:
        db.close()

    print("\n=== Test with Serializable (should not show phantom read) ===")
    t1 = threading.Thread(target=transaction_1, args=("SERIALIZABLE",))
    t2 = threading.Thread(target=transaction_2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

if __name__ == "__main__":
    run_phantom_read()