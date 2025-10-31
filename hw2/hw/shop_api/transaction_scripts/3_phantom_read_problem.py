import time
import threading
import sys
from pathlib import Path

# Add parent directory to path to allow absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from transaction_scripts.config import engine, SessionLocal
from transaction_scripts.models import Base, DemoItem

from sqlalchemy.orm import sessionmaker

# Create session with REPEATABLE READ isolation level
SessionRepeatableRead = sessionmaker(
    bind=engine.execution_options(isolation_level="REPEATABLE READ")
)


def setup_database():
    """Create tables and test data"""

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session = SessionLocal()
    try:
        items = [
            DemoItem(id=1, name="Gaming Laptop", price=75999.0, deleted=False),
            DemoItem(id=2, name="Smartphone", price=45999.0, deleted=False),
        ]
        session.add_all(items)
        session.commit()
        print("Database prepared: Gaming Laptop (75999), Smartphone (45999)")
    finally:
        session.close()


def transaction_1_read():
    """
    Transaction T1: Manager counts expensive items for report twice
    At REPEATABLE READ may see phantom reads in some databases
    """

    session = SessionRepeatableRead()
    try:

        print("\n[T1 - Manager] Transaction started (REPEATABLE READ)")
        print("[T1 - Manager] Preparing report on expensive items...")

        count_1 = (
            session.query(DemoItem).filter(DemoItem.price > 40000).count()
        )  # first count of expensive items
        print(f"[T1 - Manager] First count: {count_1} items with price > 40000")
        print("[T1 - Manager] Processing other data for report...")
        time.sleep(3)

        session.expire_all()
        count_2 = (
            session.query(DemoItem).filter(DemoItem.price > 40000).count()
        )  # second count with same condition for verification
        print(
            f"[T1 - Manager] Second count (verification): {count_2} items with price > 40000"
        )

        if count_1 != count_2:
            print(f"\nPHANTOM READ detected")
            print(f"Count changed from {count_1} to {count_2}")
            print(f"Phantom items appeared/disappeared in report")
        else:
            print(f"\nCount did NOT change (both queries returned {count_1})")
            print("In PostgreSQL REPEATABLE READ prevents Phantom Reads")
            print("thanks to MVCC mechanism (snapshot isolation)")

        session.commit()
        print("\n[T1 - Manager] Transaction completed\n")

    except Exception as e:
        print(f"[T1 - Manager] Error: {e}")
        session.rollback()
    finally:
        session.close()


def transaction_2_modify():
    """Transaction T2: Administrator adds new expensive item between T1's counts"""

    time.sleep(1)

    session = SessionLocal()
    try:
        print("\n[T2 - Admin] Transaction started (READ COMMITTED)")

        # Add new expensive item (price > 40000)
        new_item = DemoItem(
            id=3, name="Professional Camera", price=89999.0, deleted=False
        )
        session.add(new_item)

        print(f"[T2 - Admin] Adding new item: '{new_item.name}' for {new_item.price}")

        session.commit()
        print("[T2 - Admin] Changes committed")
        print("[T2 - Admin] Note: In PostgreSQL T1 will not see this row\n")

    except Exception as e:
        print(f"[T2 - Admin] Error: {e}")
        session.rollback()
    finally:
        session.close()


def main():
    """Run demonstration"""

    print("=" * 70)
    print("DEMONSTRATION: Phantom Read at REPEATABLE READ")
    print("=" * 70)
    print("Scenario: Manager counts expensive items for report,")
    print("          administrator adds new item between counts")
    print("IMPORTANT: PostgreSQL uses Snapshot Isolation for REPEATABLE READ,")
    print("           which actually prevents Phantom Reads.")
    print("           However by SQL standard they are possible at this level.")
    print("=" * 70)

    setup_database()

    # Run two transactions in parallel
    t1 = threading.Thread(target=transaction_1_read)
    t2 = threading.Thread(target=transaction_2_modify)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print("=" * 70)
    print("PostgreSQL REPEATABLE READ prevents Phantom Reads")
    print("thanks to MVCC. In other databases (e.g., MySQL InnoDB)")
    print("at REPEATABLE READ level phantom reads are possible.")
    print("=" * 70)


if __name__ == "__main__":
    main()
