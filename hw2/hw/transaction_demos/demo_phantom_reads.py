"""
Демонстрация проблемы Phantom Reads и её решения через уровни изоляции.

Phantom Reads - появление новых строк (или исчезновение существующих)
при повторном выполнении того же запроса в рамках одной транзакции.
"""

import time
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop_user:shop_password@localhost:5432/shop_db")


def demo_phantom_reads_with_repeatable_read():
    """
    Демонстрация Phantom Reads при уровне изоляции REPEATABLE READ.
    
    Примечание: В PostgreSQL при REPEATABLE READ phantom reads также не возникают,
    так как используетсяSnapshot Isolation. Однако для демонстрации концепции
    мы покажем, что может произойти в теории.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Phantom Reads с REPEATABLE READ")
    print("="*80)
    
    engine = create_engine(DATABASE_URL, isolation_level="REPEATABLE READ")
    Session = sessionmaker(bind=engine)
    
    # Подготовка данных
    session = Session()
    session.execute(text("DELETE FROM items WHERE id >= 9990 AND id <= 9995"))
    session.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (9990, 'Item A', 50.00, false)"))
    session.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (9991, 'Item B', 75.00, false)"))
    session.commit()
    session.close()
    print("[SETUP] Созданы тестовые товары с ценами 50.00 и 75.00")
    
    def transaction_1():
        """Транзакция 1: Выполняет агрегирующий запрос дважды"""
        session = Session()
        try:
            print("\n[T1] Начало транзакции 1 (REPEATABLE READ)")
            session.execute(text("BEGIN"))
            
            # Первый запрос: считаем количество товаров с ценой > 40
            result = session.execute(text("SELECT COUNT(*) FROM items WHERE price > 40 AND id >= 9990 AND id <= 9995"))
            count1 = result.scalar()
            print(f"[T1] Первый запрос: COUNT(*) = {count1}")
            
            # Ждём, пока T2 добавит новую строку
            time.sleep(2)
            
            # Второй запрос: повторяем тот же запрос
            result = session.execute(text("SELECT COUNT(*) FROM items WHERE price > 40 AND id >= 9990 AND id <= 9995"))
            count2 = result.scalar()
            print(f"[T1] Второй запрос: COUNT(*) = {count2}")
            
            if count1 != count2:
                print(f"[T1] [!!] PHANTOM READS обнаружен! Количество изменилось с {count1} на {count2}")
            else:
                print(f"[T1] [OK] Phantom Reads не произошёл. Количество осталось {count1}")
                print("[T1] [OK] В PostgreSQL REPEATABLE READ предотвращает phantom reads")
            
            session.commit()
        finally:
            session.close()
    
    def transaction_2():
        """Транзакция 2: Вставляет новую строку между запросами T1"""
        session = Session()
        try:
            time.sleep(1)  # Ждём первого запроса T1
            
            print("\n[T2] Начало транзакции 2")
            session.execute(text("BEGIN"))
            session.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (9992, 'Item C', 100.00, false)"))
            print("[T2] Вставил новый товар с price=100.00")
            session.commit()
            print("[T2] Закоммитил изменения")
            
        finally:
            session.close()
    
    # Запускаем транзакции параллельно
    t1 = threading.Thread(target=transaction_1)
    t2 = threading.Thread(target=transaction_2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    # Очистка
    session = Session()
    session.execute(text("DELETE FROM items WHERE id >= 9990 AND id <= 9995"))
    session.commit()
    session.close()
    
    print("\n" + "="*80)


def demo_no_phantom_reads_with_serializable():
    """
    Демонстрация отсутствия Phantom Reads при уровне изоляции SERIALIZABLE.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Отсутствие Phantom Reads с SERIALIZABLE")
    print("="*80)
    
    engine = create_engine(DATABASE_URL, isolation_level="SERIALIZABLE")
    Session = sessionmaker(bind=engine)
    
    # Подготовка данных
    session = Session()
    session.execute(text("DELETE FROM items WHERE id >= 9985 AND id <= 9989"))
    session.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (9985, 'Item D', 60.00, false)"))
    session.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (9986, 'Item E', 80.00, false)"))
    session.commit()
    session.close()
    print("[SETUP] Созданы тестовые товары с ценами 60.00 и 80.00")
    
    def transaction_1():
        """Транзакция 1: Выполняет агрегирующий запрос дважды с SERIALIZABLE"""
        session = Session()
        try:
            print("\n[T1] Начало транзакции 1 (SERIALIZABLE)")
            session.execute(text("BEGIN"))
            
            # Первый запрос: считаем количество товаров с ценой > 50
            result = session.execute(text("SELECT COUNT(*) FROM items WHERE price > 50 AND id >= 9985 AND id <= 9989"))
            count1 = result.scalar()
            print(f"[T1] Первый запрос: COUNT(*) = {count1}")
            
            # Ждём, пока T2 попытается добавить новую строку
            time.sleep(2)
            
            # Второй запрос: повторяем тот же запрос
            result = session.execute(text("SELECT COUNT(*) FROM items WHERE price > 50 AND id >= 9985 AND id <= 9989"))
            count2 = result.scalar()
            print(f"[T1] Второй запрос: COUNT(*) = {count2}")
            
            if count1 != count2:
                print(f"[T1] [!!] PHANTOM READS обнаружен! Количество изменилось с {count1} на {count2}")
            else:
                print(f"[T1] [OK] Phantom Reads НЕ произошёл. Количество осталось {count1}")
                print("[T1] [OK] SERIALIZABLE гарантирует полную изоляцию транзакций")
            
            session.commit()
            print("[T1] Транзакция успешно завершена")
        except Exception as e:
            print(f"[T1] Ошибка: {e}")
            session.rollback()
        finally:
            session.close()
    
    def transaction_2():
        """Транзакция 2: Пытается вставить новую строку между запросами T1"""
        session = Session()
        try:
            time.sleep(1)  # Ждём первого запроса T1
            
            print("\n[T2] Начало транзакции 2 (SERIALIZABLE)")
            session.execute(text("BEGIN"))
            session.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (9987, 'Item F', 110.00, false)"))
            print("[T2] Вставил новый товар с price=110.00")
            session.commit()
            print("[T2] Закоммитил изменения")
            
        except Exception as e:
            print(f"[T2] Возможна ошибка сериализации: {e}")
            session.rollback()
        finally:
            session.close()
    
    # Запускаем транзакции параллельно
    t1 = threading.Thread(target=transaction_1)
    t2 = threading.Thread(target=transaction_2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    # Очистка
    session = Session()
    session.execute(text("DELETE FROM items WHERE id >= 9985 AND id <= 9989"))
    session.commit()
    session.close()
    
    print("\n" + "="*80)


def demo_serialization_error():
    """
    Демонстрация ошибки сериализации при SERIALIZABLE.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Ошибка сериализации при SERIALIZABLE")
    print("="*80)
    
    engine = create_engine(DATABASE_URL, isolation_level="SERIALIZABLE")
    Session = sessionmaker(bind=engine)
    
    # Подготовка данных
    session = Session()
    session.execute(text("DELETE FROM items WHERE id >= 9980 AND id <= 9984"))
    session.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (9980, 'Item G', 70.00, false)"))
    session.commit()
    session.close()
    print("[SETUP] Создан тестовый товар с id=9980, price=70.00")
    
    def transaction_1():
        """Транзакция 1: Читает и обновляет данные"""
        session = Session()
        try:
            print("\n[T1] Начало транзакции 1 (SERIALIZABLE)")
            session.execute(text("BEGIN"))
            
            # Чтение
            result = session.execute(text("SELECT price FROM items WHERE id = 9980"))
            price = result.scalar()
            print(f"[T1] Прочитал price = {price}")
            
            time.sleep(1.5)  # Даём время T2 тоже прочитать
            
            # Обновление
            session.execute(text("UPDATE items SET price = price + 10 WHERE id = 9980"))
            print("[T1] Обновил price = price + 10")
            
            session.commit()
            print("[T1] [OK] Транзакция успешно завершена")
            
        except Exception as e:
            print(f"[T1] [!!] Ошибка сериализации: {type(e).__name__}")
            session.rollback()
        finally:
            session.close()
    
    def transaction_2():
        """Транзакция 2: Читает и обновляет те же данные"""
        session = Session()
        try:
            time.sleep(0.5)  # Небольшая задержка
            
            print("\n[T2] Начало транзакции 2 (SERIALIZABLE)")
            session.execute(text("BEGIN"))
            
            # Чтение
            result = session.execute(text("SELECT price FROM items WHERE id = 9980"))
            price = result.scalar()
            print(f"[T2] Прочитал price = {price}")
            
            time.sleep(1.5)  # Даём время T1 обновить
            
            # Обновление
            session.execute(text("UPDATE items SET price = price + 20 WHERE id = 9980"))
            print("[T2] Попытка обновить price = price + 20")
            
            session.commit()
            print("[T2] [OK] Транзакция успешно завершена")
            
        except Exception as e:
            print(f"[T2] [!!] Ошибка сериализации: {type(e).__name__}")
            print("[T2] Это ожидаемое поведение при SERIALIZABLE - одна из транзакций должна быть отменена")
            session.rollback()
        finally:
            session.close()
    
    # Запускаем транзакции параллельно
    t1 = threading.Thread(target=transaction_1)
    t2 = threading.Thread(target=transaction_2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    # Очистка
    session = Session()
    session.execute(text("DELETE FROM items WHERE id >= 9980 AND id <= 9984"))
    session.commit()
    session.close()
    
    print("\n" + "="*80)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ТЕСТИРОВАНИЕ PHANTOM READS")
    print("="*80)
    print("\nPhantom Reads - это ситуация, когда одна транзакция выполняет")
    print("один и тот же запрос дважды, но получает разное количество строк,")
    print("потому что другая транзакция добавила или удалила строки между запросами.")
    print("\nВ стандарте SQL:")
    print("- При REPEATABLE READ phantom reads возможны")
    print("- При SERIALIZABLE phantom reads невозможны")
    print("\nВ PostgreSQL:")
    print("- REPEATABLE READ использует Snapshot Isolation и предотвращает phantom reads")
    print("- SERIALIZABLE обеспечивает полную изоляцию с обнаружением конфликтов")
    
    # Демонстрация с REPEATABLE READ
    demo_phantom_reads_with_repeatable_read()
    
    # Демонстрация с SERIALIZABLE
    demo_no_phantom_reads_with_serializable()
    
    # Демонстрация ошибки сериализации
    demo_serialization_error()
    
    print("\n" + "="*80)
    print("ВЫВОД:")
    print("В PostgreSQL phantom reads предотвращаются уже на уровне REPEATABLE READ")
    print("благодаря использованию Snapshot Isolation.")
    print("SERIALIZABLE обеспечивает максимальную изоляцию, но может приводить")
    print("к ошибкам сериализации, требующим повтора транзакции.")
    print("="*80 + "\n")

