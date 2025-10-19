"""
Демонстрация проблемы Non-Repeatable Read и её решения через уровни изоляции.

Non-Repeatable Read - повторное чтение той же строки даёт разные результаты
из-за коммита другой транзакции между чтениями.
"""

import time
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop_user:shop_password@localhost:5432/shop_db")


def demo_non_repeatable_read_with_read_committed():
    """
    Демонстрация Non-Repeatable Read при уровне изоляции READ COMMITTED.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Non-Repeatable Read с READ COMMITTED")
    print("="*80)
    
    engine = create_engine(DATABASE_URL, isolation_level="READ COMMITTED")
    Session = sessionmaker(bind=engine)
    
    # Подготовка данных
    session = Session()
    session.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (9997, 'Test Item 3', 100.00, false) ON CONFLICT (id) DO UPDATE SET price = 100.00, deleted = false"))
    session.commit()
    session.close()
    print("[SETUP] Создан тестовый товар с id=9997, price=100.00")
    
    def transaction_1():
        """Транзакция 1: Читает данные дважды"""
        session = Session()
        try:
            print("\n[T1] Начало транзакции 1 (READ COMMITTED)")
            session.execute(text("BEGIN"))
            
            # Первое чтение
            result = session.execute(text("SELECT price FROM items WHERE id = 9997"))
            price1 = result.scalar()
            print(f"[T1] Первое чтение: price = {price1}")
            
            # Ждём, пока T2 обновит и закоммитит данные
            time.sleep(2)
            
            # Второе чтение той же строки
            result = session.execute(text("SELECT price FROM items WHERE id = 9997"))
            price2 = result.scalar()
            print(f"[T1] Второе чтение: price = {price2}")
            
            if price1 != price2:
                print(f"[T1] [!!] NON-REPEATABLE READ обнаружен! Цена изменилась с {price1} на {price2}")
            else:
                print(f"[T1] [OK] Non-Repeatable Read не произошёл. Цена осталась {price1}")
            
            session.commit()
        finally:
            session.close()
    
    def transaction_2():
        """Транзакция 2: Обновляет данные между чтениями T1"""
        session = Session()
        try:
            time.sleep(1)  # Ждём первого чтения T1
            
            print("\n[T2] Начало транзакции 2")
            session.execute(text("BEGIN"))
            session.execute(text("UPDATE items SET price = 200.00 WHERE id = 9997"))
            print("[T2] Обновил цену на 200.00")
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
    session.execute(text("DELETE FROM items WHERE id = 9997"))
    session.commit()
    session.close()
    
    print("\n" + "="*80)


def demo_no_non_repeatable_read_with_repeatable_read():
    """
    Демонстрация отсутствия Non-Repeatable Read при уровне изоляции REPEATABLE READ.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Отсутствие Non-Repeatable Read с REPEATABLE READ")
    print("="*80)
    
    engine = create_engine(DATABASE_URL, isolation_level="REPEATABLE READ")
    Session = sessionmaker(bind=engine)
    
    # Подготовка данных
    session = Session()
    session.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (9996, 'Test Item 4', 150.00, false) ON CONFLICT (id) DO UPDATE SET price = 150.00, deleted = false"))
    session.commit()
    session.close()
    print("[SETUP] Создан тестовый товар с id=9996, price=150.00")
    
    def transaction_1():
        """Транзакция 1: Читает данные дважды с REPEATABLE READ"""
        session = Session()
        try:
            print("\n[T1] Начало транзакции 1 (REPEATABLE READ)")
            session.execute(text("BEGIN"))
            
            # Первое чтение
            result = session.execute(text("SELECT price FROM items WHERE id = 9996"))
            price1 = result.scalar()
            print(f"[T1] Первое чтение: price = {price1}")
            
            # Ждём, пока T2 обновит и закоммитит данные
            time.sleep(2)
            
            # Второе чтение той же строки
            result = session.execute(text("SELECT price FROM items WHERE id = 9996"))
            price2 = result.scalar()
            print(f"[T1] Второе чтение: price = {price2}")
            
            if price1 != price2:
                print(f"[T1] [!!] NON-REPEATABLE READ обнаружен! Цена изменилась с {price1} на {price2}")
            else:
                print(f"[T1] [OK] Non-Repeatable Read НЕ произошёл. Цена осталась {price1}")
                print("[T1] [OK] REPEATABLE READ гарантирует согласованное чтение в рамках транзакции")
            
            session.commit()
        finally:
            session.close()
    
    def transaction_2():
        """Транзакция 2: Обновляет данные между чтениями T1"""
        session = Session()
        try:
            time.sleep(1)  # Ждём первого чтения T1
            
            print("\n[T2] Начало транзакции 2")
            session.execute(text("BEGIN"))
            session.execute(text("UPDATE items SET price = 250.00 WHERE id = 9996"))
            print("[T2] Обновил цену на 250.00")
            session.commit()
            print("[T2] Закоммитил изменения")
            print("[T2] Но T1 не увидит эти изменения из-за REPEATABLE READ")
            
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
    session.execute(text("DELETE FROM items WHERE id = 9996"))
    session.commit()
    session.close()
    
    print("\n" + "="*80)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ТЕСТИРОВАНИЕ NON-REPEATABLE READ")
    print("="*80)
    print("\nNon-Repeatable Read - это ситуация, когда одна транзакция")
    print("читает одну и ту же строку дважды, но получает разные значения,")
    print("потому что другая транзакция изменила и закоммитила данные между чтениями.")
    print("\nПри уровне изоляции READ COMMITTED это возможно.")
    print("При уровне изоляции REPEATABLE READ и выше - это невозможно.")
    
    # Демонстрация с READ COMMITTED
    demo_non_repeatable_read_with_read_committed()
    
    # Демонстрация с REPEATABLE READ
    demo_no_non_repeatable_read_with_repeatable_read()
    
    print("\n" + "="*80)
    print("ВЫВОД:")
    print("При READ COMMITTED возможен non-repeatable read.")
    print("При REPEATABLE READ транзакция видит согласованный снимок данных")
    print("на момент первого чтения, поэтому non-repeatable read невозможен.")
    print("="*80 + "\n")

