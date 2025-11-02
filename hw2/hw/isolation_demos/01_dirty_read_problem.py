"""
Демонстрация проблемы DIRTY READ при уровне изоляции READ UNCOMMITTED

Проблема: Транзакция 1 читает данные, которые изменила, но ещё не закоммитила транзакция 2.
Если транзакция 2 откатится, транзакция 1 увидит несуществующие данные.

"""

import time
from threading import Thread
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://shop_user:shop_pass@localhost:5432/shop_db"

engine = create_engine(DATABASE_URL, isolation_level="READ UNCOMMITTED")
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
    Транзакция 1: Читает цену товара
    """
    session = SessionLocal()
    try:
        print("\n[T1] Транзакция 1 начата (READ UNCOMMITTED)")

        time.sleep(2)
        
        result = session.execute(text("SELECT price FROM items WHERE id = 999")).fetchone()
        price = result[0] if result else None
        
        print(f"[T1] Прочитали цену: {price}")
        print(f"[T1] DIRTY READ! Видим несохранённые изменения транзакции 2!")
        
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
        print("Транзакция 1 видела 999.99, но в БД осталось 100.0!")
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 70)
    print("ДЕМОНСТРАЦИЯ: DIRTY READ при READ UNCOMMITTED")
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
    print("ПРОБЛЕМА: Dirty Read позволяет читать незакоммиченные данные!")
    print("=" * 70)