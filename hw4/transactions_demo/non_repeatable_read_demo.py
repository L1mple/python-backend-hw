import threading
import time

from database import SessionLocal
from models import Product
from sqlalchemy import text


def transaction_1():
    time.sleep(1)
    db = SessionLocal()
    try:
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        db.begin()

        print("Транзакция 1: Изменяем цену продукта с id=1")
        db.query(Product).filter(Product.id == 1).update({Product.price: 200.0})

        db.commit()
        print("Транзакция 1: Изменения закоммичены")
        print("Транзакция 1: Завершена")
    except Exception as e:
        print(f"Ошибка в транзакции 1: {e}")
        db.rollback()
    finally:
        db.close()


def transaction_2():
    db = SessionLocal()
    try:
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        db.begin()

        print("Транзакция 2: Первое чтение цены продукта с id=1")
        product = db.query(Product).filter(Product.id == 1).first()
        print(f"Транзакция 2: Цена продукта при первом чтении = {product.price}")

        time.sleep(2)

        print("Транзакция 2: Второе чтение цены продукта с id=1")
        product = db.query(Product).filter(Product.id == 1).first()
        print(f"Транзакция 2: Цена продукта при втором чтении = {product.price}")

        db.commit()
        print("Транзакция 2: Завершена")
    except Exception as e:
        print(f"Ошибка в транзакции 2: {e}")
        db.rollback()
    finally:
        db.close()


def setup_data():
    """Создаем тестовые данные"""
    db = SessionLocal()
    try:
        db.query(Product).delete()

        product = Product(id=1, name="Тестовый продукт", price=100.0)
        db.add(product)
        db.commit()
        print("Тестовые данные созданы")
    except Exception as e:
        print(f"Ошибка при создании тестовых данных: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    setup_data()

    t1 = threading.Thread(target=transaction_1)
    t2 = threading.Thread(target=transaction_2)

    t2.start()
    t1.start()

    t1.join()
    t2.join()

    print("Демонстрация non-repeatable read завершена")
