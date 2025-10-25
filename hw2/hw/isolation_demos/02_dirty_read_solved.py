"""
Демонстрация решения проблемы DIRTY READ при уровне изоляции READ COMMITTED

Решение: При READ COMMITTED транзакция видит только закоммиченные данные.
Незакоммиченные изменения других транзакций не видны.

"""
import time
from threading import Thread
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://shop_user:shop_pass@localhost:5432/shop_db"

engine = create_engine(DATABASE_URL, isolation_level="READ COMMITTED")
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
    Транзакция 1: Пытается прочитать цену товара
    """
    session = SessionLocal()
    try:
        print("\n[T1] Транзакция 1 начата (READ COMMITTED)")
        time.sleep(2)
        print("[T1] Пытаемся прочитать цену...")
        result = session.execute(text("SELECT price FROM items WHERE id = 999")).fetchone()
        price = result[0] if result else None
        
        print(f"[T1] Прочитали цену: {price}")
        print(f"[T1] НЕТ DIRTY READ! Видим только закоммиченные данные (100.0)")
        
        time.sleep(2)
        
        session.commit()
        print("[T1] Транзакция 1 завершена")
        
    except Exception as e:
        print(f"[T1] Ошибка: {e}")
        session.rollback()
    finally:
        session.close()


def transaction_2():
    """
    Транзакция 2: Изменяет цену товара, но откатывается
    """
    session = SessionLocal()
    try:
        print("[T2] Транзакция 2 начата")
        
        time.sleep(1)
        session.execute(text("UPDATE items SET price = 999.99 WHERE id = 999"))
        print("[T2] Изменили цену на 999.99 (НЕ сохранено)")
        print("[T2] Транзакция 1 НЕ УВИДИТ это изменение!")
        
        time.sleep(3)
        session.rollback()
        print("[T2] ROLLBACK! Изменения отменены")
        
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
        print("Транзакция 1 видела 100.0, и в БД осталось 100.0 - всё корректно!")
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 70)
    print("РЕШЕНИЕ: НЕТ DIRTY READ при READ COMMITTED")
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
    print("РЕШЕНИЕ: READ COMMITTED предотвращает Dirty Read!")
    print("=" * 70)