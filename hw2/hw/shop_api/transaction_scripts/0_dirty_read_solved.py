import time
import threading
import sys
from pathlib import Path

# Add parent directory to path to allow absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from transaction_scripts.config import engine, SessionLocal
from transaction_scripts.models import Base, DemoItem

from sqlalchemy.orm import sessionmaker

# Create session with READ UNCOMMITTED isolation level
SessionReadUncommitted = sessionmaker(
    bind=engine.execution_options(isolation_level="READ UNCOMMITTED")
)


def setup_database():
    """Create tables and test data"""

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session = SessionLocal()

    try:
        item = DemoItem(id=1, name="Laptop", price=1299.99, deleted=False)
        session.add(item)  # add transaction without commit
        session.commit()  # commit transaction
        print("Database prepared: Laptop costs 1299.99")
    finally:
        session.close()


def transaction_1_modify():
    """Transaction T1: Administrator tries to apply discount, but rolls back due to error"""

    session = SessionLocal()
    try:
        print("\n[T1 - Admin] Transaction started (READ COMMITTED)")

        item = (
            session.query(DemoItem).filter_by(id=1).first()
        )  # modify item price (apply discount)
        old_price = item.price
        item.price = 999.99

        print(
            f"[T1 - Admin] Applying discount to '{item.name}': {old_price} → {item.price}"
        )
        print("[T1 - Admin] Changes NOT committed...")
        print("[T1 - Admin] Waiting for confirmation or validation...")

        time.sleep(2)

        session.rollback()
        print("\n[T1 - Admin] ROLLBACK - discount cancelled!")
        print(f"[T1 - Admin] Price of '{item.name}' returned to 1299.99\n")

    except Exception as e:
        print(f"[T1 - Admin] Error: {e}")
        session.rollback()
    finally:
        session.close()


def transaction_2_read():
    """Transaction T2: Client tries to read the item price for purchase"""

    time.sleep(1)  # wait for T2 to modify data

    session = SessionReadUncommitted()
    try:
        print("\n[T2 - Client] Transaction started (READ UNCOMMITTED)")
        print(
            "[T2 - Client] Isolation level set: READ UNCOMMITTED but PostgreSQL uses READ COMMITTED"
        )

        item = session.query(DemoItem).filter_by(id=1).first()  # read item price
        print(f"\n[T2 - Client] Reading price of '{item.name}': {item.price}")

        if item.price == 999.99:
            print("[T2 - Client] Read uncommitted data (Dirty read)")
            print("[T2 - Client] Seeing discount price that was not confirmed!")
        else:
            print("[T2 - Client] Read only committed data")
            print("[T2 - Client] Dirty Read did NOT happen thanks to PostgreSQL")

        time.sleep(2)  # wait for T2 to ROLLBACK

        session.commit()
        print("[T2 - Client] Transaction completed\n")

    except Exception as e:
        print(f"[T2 - Client] Error: {e}")
        session.rollback()
    finally:
        session.close()


def main():
    """Run demonstration"""
    
    print("=" * 70)
    print("DEMONSTRATION: Attempt Dirty Read in PostgreSQL")
    print("=" * 70)
    print("Scenario: Client checks item price while administrator")
    print("          tries to apply discount, but rolls back changes")
    print("Goal: Show that PostgreSQL does NOT allow dirty reads")
    print("      even at READ UNCOMMITTED isolation level")
    print("=" * 70)

    setup_database()

    # Run two transactions in parallel
    t1 = threading.Thread(target=transaction_1_modify)
    T1 = threading.Thread(target=transaction_2_read)

    t1.start()
    T1.start()

    t1.join()
    T1.join()

    print("=" * 70)
    print("PostgreSQL does NOT support READ UNCOMMITTED")
    print("READ UNCOMMITTED works as READ COMMITTED")
    print("Dirty Read is impossible in PostgreSQL")
    print("=" * 70)


if __name__ == "__main__":
    main()
