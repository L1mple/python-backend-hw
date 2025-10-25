"""
Демонстрация решения проблемы NON-REPEATABLE READ при уровне изоляции REPEATABLE READ

Решение: При REPEATABLE READ транзакция видит снимок данных на момент начала.
Повторные чтения всегда возвращают одинаковый результат.

"""

import time
from threading import Thread
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://shop_user:shop_pass@localhost:5432/shop_db"

engine = create_engine(DATABASE_URL, isolation_level="REPEATABLE READ")
SessionLocal = sessionmaker(bind=engine)


def setup_test_data():
    session = SessionLocal()
    try:
        session.execute(text("DELETE FROM items WHERE id = 999"))
        session.execute(text(
            "INSERT INTO items (id, name, price, deleted) VALUES (999, 'Test Item', 100.0, false)"
        ))
        session.commit()
        print("Тестовые данные созданы: Item #999, цена = 100.0")
    finally:
        session.close()


def transaction_1():
    """
    Транзакция 1: Читает цену товара дважды
    """
    session = SessionLocal()
    try:
        print("\n[T1] Транзакция 1 начата (REPEATABLE READ)")
        result = session.execute(text("SELECT price FROM items WHERE id = 999")).fetchone()
        price_1 = result[0] if result else None
        print(f"[T1] Первое чтение: цена = {price_1}")
        print(f"[T1] Создан снимок данных на момент начала транзакции")
        time.sleep(3)
        result = session.execute(text("SELECT price FROM items WHERE id = 999")).fetchone()
        price_2 = result[0] if result else None
        print(f"[T1] Второе чтение: цена = {price_2}")
        
        if price_1 == price_2:
            print(f"[T1] REPEATABLE READ! Данные не изменились: {price_1} == {price_2}")
            print(f"[T1] Изменения других транзакций не видны")
        else:
            print(f"[T1] Неожиданно: данные изменились!")
        
        session.commit()
        print("[T1] Транзакция 1 завершена")
        
    except Exception as e:
        print(f"[T1] Ошибка: {e}")
        session.rollback()
    finally:
        session.close()


def transaction_2():
    """
    Транзакция 2: Изменяет цену товара и коммитит
    """
    session = SessionLocal()
    try:
        print("[T2] Транзакция 2 начата")
        
        time.sleep(1.5)
        session.execute(text("UPDATE items SET price = 200.0 WHERE id = 999"))
        print("[T2] Изменили цену на 200.0")
        session.commit()
        print("[T2] COMMIT! Изменения сохранены в БД")
        print("[T2] Но транзакция 1 всё равно увидит старое значение (100.0)")
        
    except Exception as e:
        print(f"[T2] Ошибка: {e}")
        session.rollback()
    finally:
        session.close()


def verify_final_state():
    session = SessionLocal()
    try:
        result = session.execute(text("SELECT price FROM items WHERE id = 999")).fetchone()
        price = result[0] if result else None
        print(f"\nФинальная цена в БД: {price}")
        print("Транзакция 1 видела 100.0 оба раза, хотя в БД уже 200.0")
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 70)
    print("РЕШЕНИЕ: НЕТ NON-REPEATABLE READ при REPEATABLE READ")
    print("=" * 70)
    
    setup_test_data()
    t1 = Thread(target=transaction_1)
    t2 = Thread(target=transaction_2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    verify_final_state()
    
    print("\n" + "=" * 70)
    print("РЕШЕНИЕ: REPEATABLE READ обеспечивает стабильность чтений!")
    print("=" * 70)