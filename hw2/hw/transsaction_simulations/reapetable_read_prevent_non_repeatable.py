"""
Prevent non-repeatable read at REPEATABLE READ in PostgreSQL (snapshot isolation).

Tx A (REPEATABLE READ):
  - SELECT price of product B
  - Sleep, then SELECT price again -> sees same price as first read

Tx B (READ COMMITTED):
  - UPDATE price of product B, COMMIT
"""

from threading import Thread

from sqlalchemy import select, update

from tx_demos.common import make_engine, products, begin_conn, reset_demo_data, sleep


def tx_a():
    eng = make_engine("REPEATABLE READ")
    with begin_conn(eng) as conn:
        price1 = conn.execute(
            select(products.c.price).where(products.c.name == "B")
        ).scalar_one()
        print(f"Tx A first read price(B) = {price1}")
        sleep(1.0)
        price2 = conn.execute(
            select(products.c.price).where(products.c.name == "B")
        ).scalar_one()
        print(f"Tx A second read price(B) = {price2}")


def tx_b():
    eng = make_engine("READ COMMITTED")
    with begin_conn(eng) as conn:
        conn.execute(
            update(products).where(products.c.name == "B").values(price=260)
        )
        print("Tx B updated price(B) to 260 and committed")


if __name__ == "__main__":
    reset_demo_data()

    t1 = Thread(target=tx_a)
    t2 = Thread(target=tx_b)

    t1.start()
    sleep(0.3)
    t2.start()

    t1.join()
    t2.join()

    print("Expect: Tx A reads same value twice at REPEATABLE READ")


