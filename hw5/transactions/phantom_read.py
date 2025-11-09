import threading
import time
from sqlalchemy import create_engine, Column, Integer, Float, insert, select
from sqlalchemy.orm import declarative_base, Session

engine = create_engine(
    "postgresql://postgres:password@localhost:5432/shop_db",
    isolation_level="SERIALIZABLE", # REPEATABLE READ | SERIALIZABLE
    future=True,
)
Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    balance = Column(Float, nullable=False)

    def __repr__(self):
        return f"<Account(id={self.id}, balance={self.balance})>"


Base.metadata.create_all(engine)

with Session(engine) as s:
    s.query(Account).delete()
    s.add_all([Account(id=1, balance=100.0), Account(id=2, balance=200.0)])
    s.commit()


def t1():
    with Session(engine) as s:
        print("T1: start")
        users1 = s.execute(select(Account)).all()
        print("T1: first read:", users1)
        time.sleep(2)
        users2 = s.execute(select(Account)).all()
        print("T1: second read:", users2)
        s.commit() # comment if REPEATABLE READ

def t2():
    with Session(engine) as s:
        time.sleep(1)
        print("T2: inserting new row")
        s.execute(insert(Account).values(id=3, balance=300))
        try:
            s.commit()
            print("T2: committed")
        except Exception as e:
            print("T2: serialization failed:", e)


th1 = threading.Thread(target=t1)
th2 = threading.Thread(target=t2)
th1.start()
th2.start()
th1.join()
th2.join()

"""
# Phantom read при REPEATABLE READ

T1: start
T1: first read: [(<Account(id=1, balance=100.0)>,), (<Account(id=2, balance=200.0)>,)]
T2: inserting new row
T2: committed
T1: second read: [(<Account(id=1, balance=100.0)>,), (<Account(id=2, balance=200.0)>,)]

# Phantom read при SERIALIZABLE

T1: start
T1: first read: [(<Account(id=1, balance=100.0)>,), (<Account(id=2, balance=200.0)>,)]
T2: inserting new row
T2: committed
T1: second read: [(<Account(id=1, balance=100.0)>,), (<Account(id=2, balance=200.0)>,)]
"""