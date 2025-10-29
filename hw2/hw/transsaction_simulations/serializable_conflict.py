"""
Show SERIALIZABLE raising serialization failure for concurrent conflicting transactions.

Scenario: both transactions read count of expensive products (>= 150) and decide to
insert a new product if count < 3. Running concurrently at SERIALIZABLE should
cause one transaction to fail with SerializationFailure.
"""

from threading import Thread

from sqlalchemy import select, func, insert
from sqlalchemy.exc import DBAPIError

from tx_demos.common import make_engine, products, begin_conn, reset_demo_data, sleep


def worker(name: str):
    eng = make_engine("SERIALIZABLE")
    try:
        with begin_conn(eng) as conn:
            cnt = conn.execute(
                select(func.count()).select_from(products).where(products.c.price >= 150)
            ).scalar_one()
            print(f"{name}: saw count(>=150) = {cnt}")
            if cnt < 3:
                conn.execute(insert(products).values(name=f"{name}_X", price=200))
                print(f"{name}: inserted new expensive product")
            else:
                print(f"{name}: did not insert")
    except DBAPIError as e:
        print(f"{name}: failed with {type(e.orig).__name__}: {e.orig}")


if __name__ == "__main__":
    reset_demo_data()

    t1 = Thread(target=worker, args=("Tx1",))
    t2 = Thread(target=worker, args=("Tx2",))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print("Expect: one transaction commits, the other fails with serialization error")


