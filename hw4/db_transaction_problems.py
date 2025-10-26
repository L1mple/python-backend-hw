import threading
import time

from sqlalchemy.orm import Session
from shop_api.main import ItemOrm, CartItemOrm, engine

def get_session_with_isolation(level: str) -> Session:
    conn = engine.connect()
    conn = conn.execution_options(isolation_level=level)
    session = Session(bind=conn)
    return session

def clear_items():
    session = get_session_with_isolation("READ COMMITTED")
    session.query(CartItemOrm).delete()
    session.query(ItemOrm).delete()
    session.commit()
    session.close()

def dirty_read_example():
    print("RUN DIRTY READ")
    clear_items()

    session1 = get_session_with_isolation("READ UNCOMMITTED")
    session2 = get_session_with_isolation("READ UNCOMMITTED")

    session1.connection()
    session2.connection()

    def t1():
        item = ItemOrm(name="DirtyItem", price=123)
        session1.add(item)
        session1.flush()
        print("T1: Inserted, not committed")
        time.sleep(3)
        session1.rollback()

    def t2():
        time.sleep(1)
        items = session2.query(ItemOrm).filter_by(name="DirtyItem").all()
        print(f"T2: Read items: {items}")

    thread1 = threading.Thread(target=t1)
    thread2 = threading.Thread(target=t2)
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()


def non_repeatable_read():
    print("\nRUN REPEATABLE READ")
    clear_items()

    session1 = get_session_with_isolation("READ COMMITTED")
    session2 = get_session_with_isolation("READ COMMITTED")

    session1.connection()
    session2.connection()

    item = ItemOrm(name="NonRepeat", price=10)
    session1.add(item)
    session1.commit()

    def t1():
        i1 = session1.query(ItemOrm).filter_by(name="NonRepeat").first()
        print(f"T1 first read: {i1.price}")
        time.sleep(3)
        i2 = session1.query(ItemOrm).filter_by(name="NonRepeat").first()
        print(f"T1 second read: {i2.price}")

    def t2():
        time.sleep(1)
        i = session2.query(ItemOrm).filter_by(name="NonRepeat").first()
        i.price = 20
        session2.commit()
        print("T2: Updated price to 20")

    thread1 = threading.Thread(target=t1)
    thread2 = threading.Thread(target=t2)
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()

def phantom_read_example():
    print("\nRUN PHANTOM READ")
    clear_items()

    session1 = get_session_with_isolation("REPEATABLE READ")
    session2 = get_session_with_isolation("REPEATABLE READ")

    session1.connection()
    session2.connection()

    def t1():
        items1 = session1.query(ItemOrm).all()
        print(f"T1 first read: {[i.name for i in items1]}")
        time.sleep(3)
        items2 = session1.query(ItemOrm).all()
        print(f"T1 second read: {[i.name for i in items2]}")

    def t2():
        time.sleep(1)
        item = ItemOrm(name="Phantom", price=50)
        session2.add(item)
        session2.commit()
        print("T2: Added Phantom")

    thread1 = threading.Thread(target=t1)
    thread2 = threading.Thread(target=t2)
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()

if __name__ == "__main__":
    dirty_read_example()
    non_repeatable_read()
    phantom_read_example()
