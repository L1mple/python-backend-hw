from sqlalchemy import create_engine, text
import threading, time

engine1 = create_engine("postgresql+psycopg2://postgres:1234@localhost:5432/shop_db",
                        isolation_level="READ COMMITTED")
engine2 = create_engine("postgresql+psycopg2://postgres:1234@localhost:5432/shop_db",
                        isolation_level="READ COMMITTED")

def txn1():
    with engine1.connect() as conn:
        trans = conn.begin()
        res1 = conn.execute(text("SELECT balance FROM accounts WHERE name='Bob'")).scalar()
        print(f"TX1: initial read Bob.balance = {res1}")
        time.sleep(4)
        res2 = conn.execute(text("SELECT balance FROM accounts WHERE name='Bob'")).scalar()
        print(f"TX1: second read Bob.balance = {res2}")
        trans.commit()

def txn2():
    time.sleep(1)
    with engine2.begin() as conn:
        conn.execute(text("UPDATE accounts SET balance = balance + 100 WHERE name='Bob'"))
        print("TX2: Bob's balance edited and committed.")

t1 = threading.Thread(target=txn1)
t2 = threading.Thread(target=txn2)
t1.start(); t2.start()
t1.join(); t2.join()
