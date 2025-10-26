"""
Демонстрация проблемы Dirty Read и её решения через уровни изоляции.

Dirty Read - чтение незафиксированных изменений из другой транзакции.
"""

import time
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop_user:shop_password@localhost:5432/shop_db")


def demo_dirty_read_with_read_uncommitted():
    """
    Демонстрация Dirty Read при уровне изоляции READ UNCOMMITTED.
    
    Примечание: PostgreSQL не поддерживает READ UNCOMMITTED,
    минимальный уровень - READ COMMITTED. Этот пример показывает,
    что dirty read не возникает даже при попытке использовать READ UNCOMMITTED.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Попытка Dirty Read с READ UNCOMMITTED")
    print("="*80)
    
    engine = create_engine(DATABASE_URL, isolation_level="READ UNCOMMITTED")
    Session = sessionmaker(bind=engine)
    
    def transaction_1():
        """Транзакция 1: Обновляет цену товара, но не коммитит сразу"""
        session = Session()
        try:
            print("\n[T1] Начало транзакции 1")
            
            # Создаём тестовый товар
            session.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (9999, 'Test Item', 100.00, false) ON CONFLICT (id) DO UPDATE SET price = 100.00, deleted = false"))
            session.commit()
            print("[T1] Создан тестовый товар с id=9999, price=100.00")
            
            # Начинаем новую транзакцию
            session.execute(text("BEGIN"))
            
            # Обновляем цену
            session.execute(text("UPDATE items SET price = 200.00 WHERE id = 9999"))
            print("[T1] Обновил цену на 200.00 (не закоммитил)")
            
            # Ждём, пока транзакция 2 попытается прочитать
            time.sleep(2)
            
            # Откатываем транзакцию
            session.rollback()
            print("[T1] Откатил транзакцию (ROLLBACK)")
            
        finally:
            session.close()
    
    def transaction_2():
        """Транзакция 2: Пытается прочитать незакоммиченные данные"""
        session = Session()
        try:
            time.sleep(1)  # Ждём, пока T1 обновит данные
            
            print("\n[T2] Начало транзакции 2")
            result = session.execute(text("SELECT price FROM items WHERE id = 9999"))
            price = result.scalar()
            print(f"[T2] Прочитал цену: {price}")
            
            if price == 200.00:
                print(f"[T2] [!!] DIRTY READ обнаружен! Прочитаны незакоммиченные данные!")
            else:
                print("[T2] [OK] Dirty Read не произошёл. Прочитаны только закоммиченные данные.")
            
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
    session.execute(text("DELETE FROM items WHERE id = 9999"))
    session.commit()
    session.close()
    
    print("\n" + "="*80)


def demo_no_dirty_read_with_read_committed():
    """
    Демонстрация отсутствия Dirty Read при уровне изоляции READ COMMITTED.
    """
    print("\n" + "="*80)
    print("ДЕМОНСТРАЦИЯ: Отсутствие Dirty Read с READ COMMITTED")
    print("="*80)
    
    engine = create_engine(DATABASE_URL, isolation_level="READ COMMITTED")
    Session = sessionmaker(bind=engine)
    
    def transaction_1():
        """Транзакция 1: Обновляет цену товара, но не коммитит сразу"""
        session = Session()
        try:
            print("\n[T1] Начало транзакции 1")
            
            # Создаём тестовый товар
            session.execute(text("INSERT INTO items (id, name, price, deleted) VALUES (9998, 'Test Item 2', 150.00, false) ON CONFLICT (id) DO UPDATE SET price = 150.00, deleted = false"))
            session.commit()
            print("[T1] Создан тестовый товар с id=9998, price=150.00")
            
            # Начинаем новую транзакцию
            session.execute(text("BEGIN"))
            
            # Обновляем цену
            session.execute(text("UPDATE items SET price = 250.00 WHERE id = 9998"))
            print("[T1] Обновил цену на 250.00 (не закоммитил)")
            
            # Ждём, пока транзакция 2 попытается прочитать
            time.sleep(2)
            
            # Откатываем транзакцию
            session.rollback()
            print("[T1] Откатил транзакцию (ROLLBACK)")
            
        finally:
            session.close()
    
    def transaction_2():
        """Транзакция 2: Читает данные с уровнем изоляции READ COMMITTED"""
        session = Session()
        try:
            time.sleep(1)  # Ждём, пока T1 обновит данные
            
            print("\n[T2] Начало транзакции 2 (READ COMMITTED)")
            result = session.execute(text("SELECT price FROM items WHERE id = 9998"))
            price = result.scalar()
            print(f"[T2] Прочитал цену: {price}")
            
            if price == 250.00:
                print("[T2] [!!] DIRTY READ обнаружен! Прочитаны незакоммиченные данные!")
            else:
                print("[T2] [OK] Dirty Read НЕ произошёл. Прочитаны только закоммиченные данные (150.00).")
            
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
    session.execute(text("DELETE FROM items WHERE id = 9998"))
    session.commit()
    session.close()
    
    print("\n" + "="*80)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ТЕСТИРОВАНИЕ DIRTY READ")
    print("="*80)
    print("\nDirty Read - это чтение незакоммиченных изменений из другой транзакции.")
    print("При уровне изоляции READ UNCOMMITTED это возможно.")
    print("При уровне изоляции READ COMMITTED и выше - это невозможно.")
    print("\nПримечание: PostgreSQL не поддерживает READ UNCOMMITTED,")
    print("минимальный уровень изоляции - READ COMMITTED.")
    
    # Попытка демонстрации с READ UNCOMMITTED (на самом деле будет READ COMMITTED)
    demo_dirty_read_with_read_uncommitted()
    
    # Демонстрация с READ COMMITTED
    demo_no_dirty_read_with_read_committed()
    
    print("\n" + "="*80)
    print("ВЫВОД:")
    print("В PostgreSQL dirty read невозможен даже при самом низком уровне изоляции,")
    print("так как минимальный поддерживаемый уровень - READ COMMITTED.")
    print("="*80 + "\n")

