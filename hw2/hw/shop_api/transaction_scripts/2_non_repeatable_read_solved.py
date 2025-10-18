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
        item = DemoItem(id=1, name="Wireless Headphones", price=2999.0, deleted=False)
        session.add(item)
        session.commit()
        print("Database prepared: Wireless Headphones cost 2999.0")
    finally:
        session.close()


def transaction_1_read():
    """
    Transaction T1: Client checks item price twice at REPEATABLE READ
    Expected result: same values at both reads
    """

    session = SessionRepeatableRead()
    try:
        print("\n[T1 - Client] Transaction started (REPEATABLE READ)")

        item = (
            session.query(DemoItem).filter_by(id=1).first()
        )  # first read of the price before checkout
        price_1 = item.price
        print(f"[T1 - Client] First read: price of '{item.name}' = {price_1}")
        print(f"[T1 - Client] Adding item to cart at price {price_1}")
        print("[T1 - Client] Got distracted for 3 seconds...")
        time.sleep(3)

        session.expire_all()
        item = (
            session.query(DemoItem).filter_by(id=1).first()
        )  # second read of THE SAME price before checkout
        price_2 = item.price
        print(
            f"[T1 - Client] Second read before purchase: price of '{item.name}' = {price_2}"
        )

        if price_1 != price_2:
            print(f"\nNON-REPEATABLE READ detected!")
            print(f"Price changed from {price_1} to {price_2}")
        else:
            print(f"\nData did NOT change (both reads returned {price_1})")
            print("REPEATABLE READ prevented Non-Repeatable Read")
            print("Client sees consistent price throughout the transaction")

        session.commit()
        print("\n[T1 - Client] Transaction completed\n")

    except Exception as e:
        print(f"[T1 - Client] Error: {e}")
        session.rollback()
    finally:
        session.close()


def transaction_2_modify():
    """Transaction T2: Administrator changes price between T1's reads"""

    time.sleep(1)  # wait for T1 to do first read

    session = SessionLocal()
    try:
        print("\n[T2 - Admin] Transaction started (READ COMMITTED)")

        item = session.query(DemoItem).filter_by(id=1).first()  # change item price
        old_price = item.price
        item.price = 3499.0

        print(
            f"[T2 - Admin] Changing price of '{item.name}': {old_price} → {item.price}"
        )

        session.commit()
        print("[T2 - Admin] Changes committed")
        print(
            "[T2 - Admin] Note: T1 will not see these changes due to REPEATABLE READ\n"
        )

    except Exception as e:
        print(f"[T2 - Admin] Error: {e}")
        session.rollback()
    finally:
        session.close()


def main():
    """Run demonstration"""

    print("=" * 70)
    print("DEMONSTRATION: Non-Repeatable Read solution with REPEATABLE READ")
    print("=" * 70)
    print("Scenario: Client checks price twice, administrator changes it,")
    print("          but thanks to REPEATABLE READ client sees consistent price")
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
    print("At REPEATABLE READ isolation level")
    print("Non-Repeatable Read problem is solved -")
    print("transaction sees consistent snapshot of data at the moment it started")
    print("=" * 70)


if __name__ == "__main__":
    main()
