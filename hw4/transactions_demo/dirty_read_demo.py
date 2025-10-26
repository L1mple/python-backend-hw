import threading
import time

from database import SessionLocal
from models import Product
from sqlalchemy import text


def transaction_1():
    """Первая транзакция - изменяет данные но не коммитит"""
    db = SessionLocal()
    try:
        # Начинаем транзакцию с уровнем изоляции READ UNCOMMITTED
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
        db.begin()

        # Изменяем данные
        print("Транзакция 1: Изменяем цену продукта с id=1")
        db.query(Product).filter(Product.id == 1).update({Product.price: 150.0})

        # Ждем немного, чтобы вторая транзакция могла прочитать не закоммиченные данные
        time.sleep(2)

        # Откатываем изменения
        print("Транзакция 1: Откатываем изменения")
        db.rollback()
        print("Транзакция 1: Завершена")
    except Exception as e:
        print(f"Ошибка в транзакции 1: {e}")
        db.rollback()
    finally:
        db.close()


def transaction_2():
    """Вторая транзакция - читает данные, которые еще не закоммичены"""
    time.sleep(1)  # Ждем, пока первая транзакция начнет изменять данные
    db = SessionLocal()
    try:
        # Начинаем транзакцию с уровнем изоляции READ UNCOMMITTED
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
        db.begin()

        # Читаем данные, которые были изменены но не закоммичены
        print("Транзакция 2: Читаем цену продукта с id=1")
        product = db.query(Product).filter(Product.id == 1).first()
        print(f"Транзакция 2: Цена продукта = {product.price}")

        # Завершаем транзакцию
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
        # Удаляем все существующие продукты
        db.query(Product).delete()

        # Создаем тестовый продукт
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
    # Создаем тестовые данные
    setup_data()

    # Запускаем две транзакции в разных потоках
    t1 = threading.Thread(target=transaction_1)
    t2 = threading.Thread(target=transaction_2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print("Демонстрация dirty read завершена")
