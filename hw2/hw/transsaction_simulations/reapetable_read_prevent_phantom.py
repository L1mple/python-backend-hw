"""
Prevent phantom read at REPEATABLE READ in PostgreSQL (snapshot isolation).

Tx A (REPEATABLE READ):
  - SELECT count(*) of products with price >= 150
  - Sleep, then SELECT count(*) again -> same count

Tx B (READ COMMITTED):
  - INSERT new product with price 180, COMMIT
"""

from threading import Thread

from sqlalchemy import select, func, insert

from tx_demos.common import make_engine, products, begin_conn, reset_demo_data, sleep


def tx_a():
    eng = make_engine("REPEATABLE READ")
    with begin_conn(eng) as conn:
        cnt1 = conn.execute(
            select(func.count()).select_from(products).where(products.c.price >= 150)
        ).scalar_one()
        print(f"Tx A first count (>=150) = {cnt1}")
        sleep(1.0)
        cnt2 = conn.execute(
            select(func.count()).select_from(products).where(products.c.price >= 150)
        ).scalar_one()
        print(f"Tx A second count (>=150) = {cnt2}")


def tx_b():
    eng = make_engine("READ COMMITTED")
    with begin_conn(eng) as conn:
        conn.execute(insert(products).values(name="C", price=180))
        print("Tx B inserted product C(price=180) and committed")


if __name__ == "__main__":
    reset_demo_data()

    t1 = Thread(target=tx_a)
    t2 = Thread(target=tx_b)

    t1.start()
    sleep(0.3)
    t2.start()

    t1.join()
    t2.join()

    print("Expect: Tx A counts same -> no phantom at REPEATABLE READ")


