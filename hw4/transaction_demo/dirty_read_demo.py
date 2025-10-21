from sqlalchemy import create_engine, text
import threading, time

# PostgreSQL treats READ UNCOMMITTED like READ COMMITTED
engine1 = create_engine("postgresql+psycopg2://postgres:1234@localhost:5432/shop_db",
                        isolation_level="READ UNCOMMITTED")
engine2 = create_engine("postgresql+psycopg2://postgres:1234@localhost:5432/shop_db",
                        isolation_level="READ UNCOMMITTED")

def txn1():
    with engine1.begin() as conn:
        conn.execute(text("UPDATE accounts SET balance = balance - 50 WHERE name='Alice'"))
        print("TX1: modification not committed...")
        time.sleep(5)
        conn.rollback()
        print("TX1: rollback done.")

def txn2():
    time.sleep(1)
    with engine2.begin() as conn:
        res = conn.execute(text("SELECT balance FROM accounts WHERE name='Alice'")).scalar()
        print(f"TX2: balance reading for Alice= {res}")

t1 = threading.Thread(target=txn1)
t2 = threading.Thread(target=txn2)
t1.start(); t2.start()
t1.join(); t2.join()
