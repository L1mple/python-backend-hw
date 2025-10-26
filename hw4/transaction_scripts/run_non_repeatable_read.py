import threading
from db_config import Item, engine
from setup_db import setup
from sqlalchemy import select, update


def reader_transaction(item_id, isolation_level, barrier):
    connection = engine.connect().execution_options(isolation_level=isolation_level)
    try:
        with connection.begin():
            print(f"READER ({isolation_level}): Started")
            stmt1 = select(Item.price).where(Item.id == item_id)
            price1 = connection.execute(stmt1).scalar_one()
            print(f"READER ({isolation_level}): First read, price={price1:.2f}")

            barrier.wait()
            barrier.wait()

            stmt2 = select(Item.price).where(Item.id == item_id)
            price2 = connection.execute(stmt2).scalar_one()
            print(f"READER ({isolation_level}): Second read, price={price2:.2f}")

            if isolation_level == 'READ COMMITTED':
                assert price1 != price2
                print(f"READER ({isolation_level}): Non-Repeatable Read!")
            else:
                assert price1 == price2
                print(f"READER ({isolation_level}): ОК")
    finally:
        connection.close()


def writer_transaction(item_id, barrier):
    barrier.wait()
    connection = engine.connect()
    try:
        with connection.begin():
            print(f"WRITER: Update price {item_id}")
            stmt = (
                update(Item)
                .where(Item.id == item_id)
                .values(price=55.55)
            )
            connection.execute(stmt)
        with connection.begin():
            check_stmt = select(Item.price).where(Item.id == item_id)
            current_price = connection.execute(check_stmt).scalar_one()
            print(f"WRITER: Check price={current_price}")
        print("WRITER: Price updated")
    finally:
        connection.close()
    barrier.wait()


if __name__ == "__main__":
    print("--- Non-Repeatable Read on level READ COMMITTED ---")
    item_id = setup()
    barrier = threading.Barrier(2, timeout=10)

    reader_thread = threading.Thread(target=reader_transaction, args=(item_id, "READ COMMITTED", barrier))
    writer_thread = threading.Thread(target=writer_transaction, args=(item_id, barrier))

    reader_thread.start()
    writer_thread.start()
    reader_thread.join()
    writer_thread.join()

    print("--- No Non-Repeatable Read on level REPEATABLE READ ---")
    item_id = setup()
    barrier = threading.Barrier(2, timeout=10)

    reader_thread = threading.Thread(target=reader_transaction, args=(item_id, "REPEATABLE READ", barrier))
    writer_thread = threading.Thread(target=writer_transaction, args=(item_id, barrier))

    reader_thread.start()
    writer_thread.start()
    reader_thread.join()
    writer_thread.join()
