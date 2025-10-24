import threading
import time
from sqlalchemy import create_engine, Column, Integer, Float, select, update
from sqlalchemy.orm import declarative_base, Session

engine = create_engine(
    "postgresql://postgres:password@localhost:5432/shop_db",
    isolation_level="REPEATABLE READ", # READ COMMITTED | REPEATABLE READ
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
        row1 = s.execute(select(Account).where(Account.id == 1)).first()
        print("T1: first read:", row1)
        time.sleep(2)
        
        s.expire_all()

        row2 = s.execute(select(Account).where(Account.id == 1)).first()
        print("T1: second read:", row2)


def t2():
    with Session(engine) as s:
        time.sleep(1)
        print("T2: updating...")
        s.execute(update(Account).where(Account.id == 1).values(balance=500))
        s.commit()
        print("T2: committed")


th1 = threading.Thread(target=t1)
th2 = threading.Thread(target=t2)
th1.start()
th2.start()
th1.join()
th2.join()

"""
# Non-repeatable read при READ COMMITTED

T1: start
T1: first read: (<Account(id=1, balance=100.0)>,)
T2: updating...
T2: committed
T1: second read: (<Account(id=1, balance=500.0)>,)

# Non-repeatable read при REPEATABLE READ

T1: start
T1: first read: (<Account(id=1, balance=100.0)>,)
T2: updating...
T2: committed
T1: second read: (<Account(id=1, balance=100.0)>,)
"""