import threading
import time

from database import SessionLocal
from models import Product
from sqlalchemy import text


def dirty_read_solution():
    """Демонстрация решения проблемы dirty read с помощью READ COMMITTED"""

    def transaction_1():
        """Первая транзакция - изменяет данные но не коммитит"""
        db = SessionLocal()
        try:
            # Начинаем транзакцию с уровнем изоляции READ COMMITTED
            db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            db.begin()

            # Изменяем данные
            print("Транзакция 1: Изменяем цену продукта с id=1")
            db.query(Product).filter(Product.id == 1).update({Product.price: 150.0})

            # Ждем немного, чтобы вторая транзакция могла попытаться прочитать не закоммиченные данные
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
        """Вторая транзакция - пытается читать данные, которые еще не закоммичены"""
        time.sleep(1)  # Ждем, пока первая транзакция начнет изменять данные
        db = SessionLocal()
        try:
            # Начинаем транзакцию с уровнем изоляции READ COMMITTED
            db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            db.begin()

            # Пытаемся читать данные, которые были изменены но не закоммичены
            print("Транзакция 2: Пытаемся читать цену продукта с id=1")
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

    print("=== Демонстрация решения проблемы dirty read ===")
    # Создаем тестовые данные
    setup_data()

    # Запускаем две транзакции в разных потоках
    t1 = threading.Thread(target=transaction_1)
    t2 = threading.Thread(target=transaction_2)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    print("Демонстрация решения dirty read завершена\n")


def non_repeatable_read_solution():
    """Демонстрация решения проблемы non-repeatable read с помощью REPEATABLE READ"""

    def transaction_1():
        """Первая транзакция - изменяет данные между чтениями второй транзакции"""
        time.sleep(1)  # Ждем, пока вторая транзакция начнет чтение
        db = SessionLocal()
        try:
            # Начинаем транзакцию с уровнем изоляции REPEATABLE READ
            db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            db.begin()

            # Пытаемся изменить данные
            print("Транзакция 1: Пытаемся изменить цену продукта с id=1")
            try:
                db.query(Product).filter(Product.id == 1).update({Product.price: 200.0})
                db.commit()
                print("Транзакция 1: Изменения закоммичены")
            except Exception as e:
                print(f"Транзакция 1: Не удалось изменить данные из-за блокировки: {e}")
                db.rollback()
            print("Транзакция 1: Завершена")
        except Exception as e:
            print(f"Ошибка в транзакции 1: {e}")
            db.rollback()
        finally:
            db.close()

    def transaction_2():
        """Вторая транзакция - читает одни и те же данные дважды"""
        db = SessionLocal()
        try:
            # Начинаем транзакцию с уровнем изоляции REPEATABLE READ
            db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            db.begin()

            # Первое чтение
            print("Транзакция 2: Первое чтение цены продукта с id=1")
            product = db.query(Product).filter(Product.id == 1).first()
            print(f"Транзакция 2: Цена продукта при первом чтении = {product.price}")

            # Ждем, пока первая транзакция попытается изменить данные
            time.sleep(2)

            # Второе чтение тех же данных
            print("Транзакция 2: Второе чтение цены продукта с id=1")
            product = db.query(Product).filter(Product.id == 1).first()
            print(f"Транзакция 2: Цена продукта при втором чтении = {product.price}")

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

    print("=== Демонстрация решения проблемы non-repeatable read ===")
    # Создаем тестовые данные
    setup_data()

    # Запускаем две транзакции в разных потоках
    t1 = threading.Thread(target=transaction_1)
    t2 = threading.Thread(target=transaction_2)

    t2.start()  # Сначала запускаем вторую транзакцию
    t1.start()  # Затем первую

    t1.join()
    t2.join()

    print("Демонстрация решения non-repeatable read завершена\n")


def phantom_read_solution():
    """Демонстрация решения проблемы phantom read с помощью SERIALIZABLE"""
    from models import Order

    def transaction_1():
        """Первая транзакция - добавляет новый продукт"""
        time.sleep(1)  # Ждем, пока вторая транзакция начнет чтение
        db = SessionLocal()
        try:
            # Начинаем транзакцию с уровнем изоляции SERIALIZABLE
            db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            db.begin()

            # Пытаемся добавить новый продукт
            print("Транзакция 1: Пытаемся добавить новый продукт")
            try:
                new_product = Product(id=2, name="Новый продукт", price=300.0)
                db.add(new_product)
                db.commit()
                print("Транзакция 1: Новый продукт добавлен")
            except Exception as e:
                print(
                    f"Транзакция 1: Не удалось добавить продукт из-за блокировки: {e}"
                )
                db.rollback()
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
            # Начинаем транзакцию с уровнем изоляции SERIALIZABLE
            db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            db.begin()

            # Первое чтение - получаем список всех продуктов
            print("Транзакция 2: Первое чтение списка продуктов")
            products1 = db.query(Product).all()
            print(
                f"Транзакция 2: Количество продуктов при первом чтении = {len(products1)}"
            )
            for product in products1:
                print(f"  - {product.name}: {product.price}")

            # Ждем, пока первая транзакция попытается добавить новый продукт
            time.sleep(2)

            # Второе чтение - снова получаем список всех продуктов
            print("Транзакция 2: Второе чтение списка продуктов")
            products2 = db.query(Product).all()
            print(
                f"Транзакция 2: Количество продуктов при втором чтении = {len(products2)}"
            )
            for product in products2:
                print(f"  - {product.name}: {product.price}")

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
            # Удаляем все существующие продукты и заказы
            db.query(Order).delete()
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

    print("=== Демонстрация решения проблемы phantom read ===")
    # Создаем тестовые данные
    setup_data()

    # Запускаем две транзакции в разных потоках
    t1 = threading.Thread(target=transaction_1)
    t2 = threading.Thread(target=transaction_2)

    t2.start()  # Сначала запускаем вторую транзакцию
    t1.start()  # Затем первую

    t1.join()
    t2.join()

    print("Демонстрация решения phantom read завершена\n")


def setup_data():
    """Создаем тестовые данные"""
    db = SessionLocal()
    try:
        # Удаляем все существующие продукты и заказы
        db.query(Product).delete()

        # Создаем тестовый продукт
        product = Product(id=1, name="Тестовый продукт", price=100.0)
        db.add(product)
        db.commit()
        print("Общие тестовые данные созданы")
    except Exception as e:
        print(f"Ошибка при создании тестовых данных: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Создаем тестовые данные
    setup_data()

    # Демонстрируем решения всех трех проблем
    dirty_read_solution()
    non_repeatable_read_solution()
    phantom_read_solution()

    print("Все демонстрации решений завершены")
