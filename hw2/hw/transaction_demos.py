import time
from threading import Thread
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://shop_user:shop_password@localhost:5432/shop_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def setup_test_data():
    db = SessionLocal()
    db.execute(text("DELETE FROM cart_items"))
    db.execute(text("DELETE FROM items"))
    db.execute(text("DELETE FROM carts"))
    db.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (1, 'Test Item', 100.0, false)"))
    db.commit()
    db.close()
    print("Тестовые данные созданы\n")


# 1. Dirty Read
def demo_dirty_read_uncommitted():
    print("1. DIRTY READ при READ UNCOMMITTED")
    setup_test_data()

    def transaction1():
        db = SessionLocal()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
        db.execute(text("UPDATE items SET price = 200.0 WHERE id = 1"))
        print("T1: Изменил цену на 200, но НЕ коммитнул")
        time.sleep(2)
        db.rollback()
        print("T1: Откатил изменения (rollback)")
        db.close()

    def transaction2():
        time.sleep(0.5)
        db = SessionLocal()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
        result = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()
        print(f"T2: Прочитал цену = {result[0]} (dirty read!)")
        db.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print()


def demo_no_dirty_read_committed():
    print("2. НЕТ DIRTY READ при READ COMMITTED")
    setup_test_data()

    def transaction1():
        db = SessionLocal()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        db.execute(text("UPDATE items SET price = 200.0 WHERE id = 1"))
        print("T1: Изменил цену на 200, но НЕ коммитнул")
        time.sleep(2)
        db.rollback()
        print("T1: Откатил изменения")
        db.close()

    def transaction2():
        time.sleep(0.5)
        db = SessionLocal()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        result = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()
        print(f"T2: Прочитал цену = {result[0]} (старое значение, нет dirty read!)")
        db.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    print()


# 3. Non-repeatable Read
def demo_nonrepeatable_read_committed():
    print("3. NON-REPEATABLE READ при READ COMMITTED")
    setup_test_data()

    def transaction1():
        time.sleep(1)
        db = SessionLocal()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        db.execute(text("UPDATE items SET price = 300.0 WHERE id = 1"))
        db.commit()
        print("T1: Изменил и закоммитил цену на 300")
        db.close()

    def transaction2():
        db = SessionLocal()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        result1 = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()
        print(f"T2: Первое чтение цены = {result1[0]}")
        time.sleep(2)
        result2 = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()
        print(f"T2: Второе чтение цены = {result2[0]} (non-repeatable read!)")
        db.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    t2.start()
    t1.start()
    t1.join()
    t2.join()
    print()


def demo_no_nonrepeatable_read_repeatable():
    print("4. НЕТ NON-REPEATABLE READ при REPEATABLE READ")
    setup_test_data()

    def transaction1():
        time.sleep(1)
        db = SessionLocal()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        db.execute(text("UPDATE items SET price = 300.0 WHERE id = 1"))
        db.commit()
        print("T1: Изменил и закоммитил цену на 300")
        db.close()

    def transaction2():
        db = SessionLocal()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        result1 = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()
        print(f"T2: Первое чтение цены = {result1[0]}")
        time.sleep(2)
        result2 = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()
        print(f"T2: Второе чтение цены = {result2[0]} (то же значение!)")
        db.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    t2.start()
    t1.start()
    t1.join()
    t2.join()
    print()


# 5. Phantom Read
def demo_phantom_read_repeatable():
    print("5. PHANTOM READS при REPEATABLE READ")
    setup_test_data()

    def transaction1():
        time.sleep(1)
        db = SessionLocal()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        db.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (2, 'New Item', 150.0, false)"))
        db.commit()
        print("T1: Добавил новый товар с id=2")
        db.close()

    def transaction2():
        db = SessionLocal()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        result1 = db.execute(text("SELECT COUNT(*) FROM items")).fetchone()
        print(f"T2: Первый подсчёт товаров = {result1[0]}")
        time.sleep(2)
        result2 = db.execute(text("SELECT COUNT(*) FROM items")).fetchone()
        print(f"T2: Второй подсчёт товаров = {result2[0]} (phantom read!)")
        db.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    t2.start()
    t1.start()
    t1.join()
    t2.join()
    print()


def demo_no_phantom_read_serializable():
    print("6. НЕТ PHANTOM READS при SERIALIZABLE")
    setup_test_data()

    def transaction1():
        time.sleep(1)
        db = SessionLocal()
        try:
            db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            db.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (3, 'Another Item', 175.0, false)"))
            db.commit()
            print("T1: Добавил новый товар")
        except Exception as e:
            print(f"T1: Ошибка при попытке добавить товар (сериализация!)")
            db.rollback()
        finally:
            db.close()

    def transaction2():
        db = SessionLocal()
        db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
        result1 = db.execute(text("SELECT COUNT(*) FROM items")).fetchone()
        print(f"T2: Первый подсчёт товаров = {result1[0]}")
        time.sleep(2)
        result2 = db.execute(text("SELECT COUNT(*) FROM items")).fetchone()
        print(f"T2: Второй подсчёт товаров = {result2[0]} (то же значение!)")
        db.commit()
        db.close()

    t1 = Thread(target=transaction1)
    t2 = Thread(target=transaction2)
    t2.start()
    t1.start()
    t1.join()
    t2.join()
    print()


if __name__ == "__main__":

    demo_dirty_read_uncommitted()
    demo_no_dirty_read_committed()
    demo_nonrepeatable_read_committed()
    demo_no_nonrepeatable_read_repeatable()
    demo_phantom_read_repeatable()
    demo_no_phantom_read_serializable()
