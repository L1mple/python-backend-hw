import threading
from db_config import Item, engine, SessionLocal
from setup_db import setup
from sqlalchemy import select, update


def transaction_a(item_id, barrier):
    connection = engine.connect().execution_options(isolation_level="READ COMMITTED")
    try:
        with connection.begin() as transaction:
            print("Transaction A started. Try set price 99.99")
            stmt = (
                update(Item)
                .where(Item.id == item_id)
                .values(price=55.55)
            )
            connection.execute(stmt)
            print("Transaction A price updated and flushed")
            barrier.wait()
            barrier.wait()
            stmt = select(Item.price).where(Item.id == item_id)
            price = connection.execute(stmt).scalar_one()
            print(f"Transaction A has price {price}")
            assert price == 55.55
            print("Transaction A do rollback")
            transaction.rollback()
    finally:
        connection.close()


def transaction_b(item_id, barrier):
    connection = engine.connect().execution_options(isolation_level="READ COMMITTED")
    try:
        barrier.wait()
        with connection.begin():
            print("Transaction B read price")
            stmt = select(Item.price).where(Item.id == item_id)
            price = connection.execute(stmt).scalar_one()
            assert price == 10.0
            print(f"Transaction B price={price:.2f}. No dirty read! Sleep")
        barrier.wait()
    finally:
        connection.close()


if __name__ == "__main__":
    print("--- Postgresql: no Dirty read. All READ COMMITTED ---")
    item_id = setup()

    barrier = threading.Barrier(2, timeout=10)
    thread_a = threading.Thread(target=transaction_a, args=(item_id, barrier))
    thread_b = threading.Thread(target=transaction_b, args=(item_id, barrier))

    thread_a.start()
    thread_b.start()

    thread_a.join()
    thread_b.join()

    final_session = SessionLocal()
    final_item = final_session.query(Item).get(item_id)
    print(f"Final price: {final_item.price:.2f}")
    assert final_item.price == 10.0
    final_session.close()
