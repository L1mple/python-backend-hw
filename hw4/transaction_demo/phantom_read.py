from sqlalchemy import create_engine, text
import threading, time

engine1 = create_engine("postgresql+psycopg2://postgres:1234@localhost:5432/shop_db",
                        isolation_level="REPEATABLE READ")
engine2 = create_engine("postgresql+psycopg2://postgres:1234@localhost:5432/shop_db",
                        isolation_level="REPEATABLE READ")

def txn1():
    with engine1.connect() as conn:
        trans = conn.begin()
        res1 = conn.execute(text("SELECT COUNT(*) FROM accounts WHERE balance > 100")).scalar()
        print(f"TX1: first SELECT => {res1} account > 100")
        time.sleep(4)
        res2 = conn.execute(text("SELECT COUNT(*) FROM accounts WHERE balance > 100")).scalar()
        print(f"TX1: second SELECT => {res2} account > 100")
        trans.commit()

def txn2():
    time.sleep(1)
    with engine2.begin() as conn:
        conn.execute(text("INSERT INTO accounts (name, balance) VALUES ('Charlie', 150)"))
        print("TX2: Charlie added with balance 150.")

t1 = threading.Thread(target=txn1)
t2 = threading.Thread(target=txn2)
t1.start(); t2.start()
t1.join(); t2.join()
