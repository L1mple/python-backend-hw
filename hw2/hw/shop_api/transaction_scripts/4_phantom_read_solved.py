import time
import threading
import sys
from pathlib import Path

# Add parent directory to path to allow absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.exc import OperationalError
from transaction_scripts.config import engine, SessionLocal
from transaction_scripts.models import Base, DemoItem

from sqlalchemy.orm import sessionmaker

# Create session with SERIALIZABLE isolation level
SessionSerializable = sessionmaker(
    bind=engine.execution_options(isolation_level="SERIALIZABLE")
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
    At SERIALIZABLE phantom reads are guaranteed to not occur
    """

    # session = SessionLocal()
    session = SessionSerializable()
    try:
        # Set SERIALIZABLE isolation level
        # session.connection(execution_options={"isolation_level": "SERIALIZABLE"})

        print("\n[T1 - Manager] Transaction started (SERIALIZABLE)")
        print("[T1 - Manager] Preparing critical report on expensive items...")

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
        else:
            print(f"\nCount did NOT change (both queries returned {count_1})")
            print("SERIALIZABLE prevented Phantom Reads")
            print("Report will be fully consistent")

        session.commit()
        print("\n[T1 - Manager] Transaction completed successfully\n")

    except OperationalError as e:
        if "could not serialize" in str(e):
            print(f"\n[T1 - Manager] Serialization error!")
            print(f"PostgreSQL detected a conflict and cancelled the transaction")
            print(f"This is normal behavior at SERIALIZABLE")
        else:
            print(f"[T1 - Manager] Error: {e}")
        session.rollback()
    except Exception as e:
        print(f"[T1 - Manager] Error: {e}")
        session.rollback()
    finally:
        session.close()


def transaction_2_modify():
    """
    Transaction T2: Administrator adds new expensive item between T1's counts
    At READ COMMITTED phantom reads are guaranteed to not occur
    """

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
        print("[T2 - Admin] Changes committed successfully\n")

    except Exception as e:
        print(f"[T2 - Admin] Error: {e}")
        session.rollback()
    finally:
        session.close()


def main():
    """Run demonstration"""
    print("=" * 70)
    print("DEMONSTRATION: Phantom Read solution with SERIALIZABLE")
    print("=" * 70)
    print("Scenario: Manager prepares report at SERIALIZABLE,")
    print("          administrator adds item - PostgreSQL prevents")
    print("          phantom reads, guaranteeing full isolation")
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
    print("At SERIALIZABLE isolation level PostgreSQL")
    print("guarantees absence of all anomalies, including Phantom Reads.")
    print("=" * 70)


if __name__ == "__main__":
    main()
