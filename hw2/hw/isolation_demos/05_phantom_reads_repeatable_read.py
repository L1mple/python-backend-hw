"""
Демонстрация проблемы PHANTOM READS при уровне изоляции REPEATABLE READ

Проблема: Транзакция выполняет один и тот же запрос дважды, но получает разное количество строк,
потому что другая транзакция добавила или удалила строки между запросами.

Phantom Read отличается от Non-Repeatable Read:
- Non-Repeatable Read: изменение существующих строк
- Phantom Read: появление/исчезновение строк (INSERT/DELETE)

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
        session.execute(text("DELETE FROM items WHERE id BETWEEN 990 AND 999"))
        session.execute(text(
            "INSERT INTO items (id, name, price, deleted) VALUES "
            "(990, 'Cheap Item 1', 50.0, false), "
            "(991, 'Cheap Item 2', 60.0, false)"
        ))
        session.commit()
        print("Тестовые данные созданы: 2 товара с ценой <= 100")
    finally:
        session.close()


def transaction_1():
    """
    Транзакция 1: Подсчитывает товары дважды
    """
    session = SessionLocal()
    try:
        print("\n[T1] Транзакция 1 начата (REPEATABLE READ)")
        result = session.execute(text(
            "SELECT COUNT(*) FROM items WHERE price <= 100 AND deleted = false"
        )).fetchone()
        count_1 = result[0] if result else 0
        print(f"[T1] Первый подсчёт: {count_1} товаров с ценой <= 100")
        items = session.execute(text(
            "SELECT id, name, price FROM items WHERE price <= 100 AND deleted = false"
        )).fetchall()
        print(f"[T1] Товары: {[(item[0], item[1], item[2]) for item in items]}")
        time.sleep(3)
        result = session.execute(text(
            "SELECT COUNT(*) FROM items WHERE price <= 100 AND deleted = false"
        )).fetchone()
        count_2 = result[0] if result else 0
        print(f"[T1] Второй подсчёт: {count_2} товаров с ценой <= 100")
        items = session.execute(text(
            "SELECT id, name, price FROM items WHERE price <= 100 AND deleted = false"
        )).fetchall()
        print(f"[T1] Товары: {[(item[0], item[1], item[2]) for item in items]}")
        
        if count_1 != count_2:
            print(f"[T1] PHANTOM READ! Количество строк изменилось: {count_1} → {count_2}")
            print(f"[T1] Появились 'призрачные' строки!")
        else:
            print(f"[T1] Количество строк не изменилось: {count_1} == {count_2}")
        
        session.commit()
        print("[T1] Транзакция 1 завершена")
        
    except Exception as e:
        print(f"[T1] Ошибка: {e}")
        session.rollback()
    finally:
        session.close()


def transaction_2():
    """
    Транзакция 2: Добавляет новый дешёвый товар
    """
    session = SessionLocal()
    try:
        print("[T2] Транзакция 2 начата")
        
        time.sleep(1.5)
        session.execute(text(
            "INSERT INTO items (id, name, price, deleted) VALUES (992, 'Cheap Item 3', 70.0, false)"
        ))
        print("[T2] Добавили новый товар: 'Cheap Item 3' за 70.0")
 
        session.commit()
        print("[T2] COMMIT! Новый товар сохранён")
        print("[T2] При REPEATABLE READ в PostgreSQL транзакция 1 НЕ увидит новую строку")
        
    except Exception as e:
        print(f"[T2] Ошибка: {e}")
        session.rollback()
    finally:
        session.close()


def verify_final_state():
    session = SessionLocal()
    try:
        result = session.execute(text(
            "SELECT COUNT(*) FROM items WHERE price <= 100 AND deleted = false"
        )).fetchone()
        count = result[0] if result else 0
        print(f"\nФинальное количество товаров в БД: {count}")
        
        items = session.execute(text(
            "SELECT id, name, price FROM items WHERE price <= 100 AND deleted = false"
        )).fetchall()
        print(f"Все товары: {[(item[0], item[1], item[2]) for item in items]}")
        
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 70)
    print("ДЕМОНСТРАЦИЯ: PHANTOM READS при REPEATABLE READ (PostgreSQL)")
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
    print("В PostgreSQL: REPEATABLE READ уже блокирует Phantom Reads")
    print("=" * 70)