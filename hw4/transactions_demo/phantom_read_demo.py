import threading
import time

from database import SessionLocal
from models import Order, Product
from sqlalchemy import text


def transaction_1():
    time.sleep(1)
    db = SessionLocal()
    try:
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        db.begin()

        print("Транзакция 1: Добавляем новый продукт")
        new_product = Product(id=2, name="Новый продукт", price=300.0)
        db.add(new_product)

        db.commit()
        print("Транзакция 1: Новый продукт добавлен")
        print("Транзакция 1: Завершена")
    except Exception as e:
        print(f"Ошибка в транзакции 1: {e}")
        db.rollback()
    finally:
        db.close()


def transaction_2():
    """Вторая транзакция - читает список продуктов дважды"""
    db = SessionLocal()
    try:
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        db.begin()

        print("Транзакция 2: Первое чтение списка продуктов")
        products1 = db.query(Product).all()
        print(
            f"Транзакция 2: Количество продуктов при первом чтении = {len(products1)}"
        )
        for product in products1:
            print(f"  - {product.name}: {product.price}")

        time.sleep(2)

        print("Транзакция 2: Второе чтение списка продуктов")
        products2 = db.query(Product).all()
        print(
            f"Транзакция 2: Количество продуктов при втором чтении = {len(products2)}"
        )
        for product in products2:
            print(f"  - {product.name}: {product.price}")

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
        db.query(Order).delete()
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

    print("Демонстрация phantom read завершена")
