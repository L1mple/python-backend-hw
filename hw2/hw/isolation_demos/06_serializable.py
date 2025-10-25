"""
Демонстрация уровня изоляции SERIALIZABLE

SERIALIZABLE - самый строгий уровень изоляции, который предотвращает все проблемы:
- Dirty Reads
- Non-Repeatable Reads  
- Phantom Reads

Транзакции выполняются так, как будто они идут последовательно, одна за другой.
Если возникает конфликт, одна из транзакций будет отменена с ошибкой сериализации.

"""

import time
from threading import Thread
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

DATABASE_URL = "postgresql://shop_user:shop_pass@localhost:5432/shop_db"

engine = create_engine(DATABASE_URL, isolation_level="SERIALIZABLE")
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
    Транзакция 1: Читает цену и пытается обновить на основе прочитанного
    """
    session = SessionLocal()
    try:
        print("\n[T1] Транзакция 1 начата (SERIALIZABLE)")
        result = session.execute(text("SELECT price FROM items WHERE id = 999")).fetchone()
        price = result[0] if result else None
        print(f"[T1] Прочитали цену: {price}")
        
        time.sleep(2)
        new_price = price * 1.1
        print(f"[T1] Пытаемся обновить цену на {new_price}")
        session.execute(text(f"UPDATE items SET price = {new_price} WHERE id = 999"))
        
        time.sleep(1)
        
        session.commit()
        print("[T1] Транзакция 1 успешно завершена")
        
    except OperationalError as e:
        print(f"[T1] ОШИБКА СЕРИАЛИЗАЦИИ!")
        print(f"[T1] {str(e)}")
        print(f"[T1] База данных обнаружила конфликт и отменила транзакцию")
        session.rollback()
    except Exception as e:
        print(f"[T1] Ошибка: {e}")
        session.rollback()
    finally:
        session.close()


def transaction_2():
    """
    Транзакция 2: Также читает цену и пытается обновить
    """
    session = SessionLocal()
    try:
        print("[T2] Транзакция 2 начата (SERIALIZABLE)")
        
        time.sleep(0.5)
        result = session.execute(text("SELECT price FROM items WHERE id = 999")).fetchone()
        price = result[0] if result else None
        print(f"[T2] Прочитали цену: {price}")
        
        time.sleep(1.5)
        new_price = price * 1.2
        print(f"[T2] Пытаемся обновить цену на {new_price}")
        session.execute(text(f"UPDATE items SET price = {new_price} WHERE id = 999"))
        
        time.sleep(1)
        
        session.commit()
        print("[T2] Транзакция 2 успешно завершена")
        
    except OperationalError as e:
        print(f"[T2] ОШИБКА СЕРИАЛИЗАЦИИ!")
        print(f"[T2] {str(e)}")
        print(f"[T2] База данных обнаружила конфликт и отменила транзакцию")
        session.rollback()
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
        print("Только одна транзакция завершилась успешно")
        print("Другая была отменена из-за конфликта сериализации")
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 70)
    print("ДЕМОНСТРАЦИЯ: SERIALIZABLE изоляция")
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
    print("SERIALIZABLE предотвращает ВСЕ аномалии, но ценой производительности")
    print("Конфликтующие транзакции будут отменяться")
    print("=" * 70)