from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import threading
import time

DATABASE_URL = "postgresql://user:password@db:5432/mydb"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def prepare_test_environment():
    """Подготовка окружения для тестирования"""
    with Session() as db:
        try:
            db.execute(text("DELETE FROM cart_items WHERE item_id = 1"))
            db.execute(text("DELETE FROM items WHERE id = 1"))
            db.execute(text("""
                INSERT INTO items (id, name, price, deleted)
                VALUES (1, 'Demo Product', 150.0, false)
            """))
            db.commit()
            print("[Setup] Тестовые данные инициализированы")
            print(f"[Setup] Создан продукт #1 с ценой 150.0\n")
        except Exception as e:
            db.rollback()
            print(f"[Error] Ошибка подготовки данных: {e}")
            raise

def show_isolation_level(db):
    level = db.execute(text("SHOW transaction_isolation")).fetchone()[0]
    print(f"[Level] Текущий уровень: {level.upper()}")

def demonstrate_dirty_read_behavior():
    print("\n=== ТЕСТ: ЧТЕНИЕ НЕЗАВЕРШЕННЫХ ДАННЫХ ===\n")
    print("PostgreSQL не поддерживает READ UNCOMMITTED, используем READ COMMITTED")

    def first_transaction():
        with Session() as db:
            print("[Tx1] Начало транзакции")
            db.execute(text("BEGIN"))
            price = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()[0]
            print(f"[Tx1] Текущая цена: {price:.2f}")
            db.execute(text("UPDATE items SET price = 200 WHERE id = 1"))
            print("[Tx1] Цена изменена на 200 (не подтверждено)")
            time.sleep(2)
            db.rollback()
            print("[Tx1] Отмена изменений")

    def second_transaction():
        time.sleep(1)
        with Session() as db:
            print("[Tx2] Чтение данных")
            price = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()[0]
            print(f"[Tx2] Полученная цена: {price:.2f}")

    t1 = threading.Thread(target=first_transaction)
    t2 = threading.Thread(target=second_transaction)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def demonstrate_changing_reads():
    print("\n=== ТЕСТ: ИЗМЕНЕНИЕ ДАННЫХ ПРИ ЧТЕНИИ ===\n")

    def read_operation():
        with Session() as db:
            db.execute(text("BEGIN ISOLATION LEVEL READ COMMITTED"))
            print("[Reader] Начало чтения (READ COMMITTED)")
            show_isolation_level(db)
            price = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()[0]
            print(f"[Reader] Первое чтение: {price:.2f}")
            time.sleep(2)
            price = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()[0]
            print(f"[Reader] Второе чтение: {price:.2f}")

    def write_operation():
        time.sleep(1)
        with Session() as db:
            print("[Writer] Изменение данных")
            db.execute(text("UPDATE items SET price = 250 WHERE id = 1"))
            db.commit()
            print("[Writer] Изменения сохранены")

    t1 = threading.Thread(target=read_operation)
    t2 = threading.Thread(target=write_operation)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def demonstrate_consistent_reads():
    print("\n=== ТЕСТ: СОГЛАСОВАННОСТЬ ДАННЫХ ===\n")

    def read_operation():
        with Session() as db:
            db.execute(text("BEGIN ISOLATION LEVEL REPEATABLE READ"))
            print("[Reader] Начало чтения (REPEATABLE READ)")
            show_isolation_level(db)
            price = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()[0]
            print(f"[Reader] Первое чтение: {price:.2f}")
            time.sleep(2)
            price = db.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()[0]
            print(f"[Reader] Второе чтение: {price:.2f}")

    def write_operation():
        time.sleep(1)
        with Session() as db:
            print("[Writer] Попытка изменения")
            db.execute(text("UPDATE items SET price = 300 WHERE id = 1"))
            db.commit()
            print("[Writer] Изменения выполнены (но не видны читателю)")

    t1 = threading.Thread(target=read_operation)
    t2 = threading.Thread(target=write_operation)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def demonstrate_phantom_reads():
    print("\n=== ТЕСТ: ФАНТОМНЫЕ ДАННЫЕ ===\n")

    with Session() as db:
        db.execute(text("DELETE FROM items WHERE name LIKE 'X%'"))
        db.execute(text("INSERT INTO items (name, price) VALUES ('X1', 100)"))
        db.commit()
        print("[Setup] Подготовлены тестовые данные X-серии")

    def read_operation():
        with Session() as db:
            db.execute(text("BEGIN ISOLATION LEVEL READ COMMITTED"))
            print("[Reader] Начало чтения")
            count = db.execute(text("SELECT COUNT(*) FROM items WHERE name LIKE 'X%'")).fetchone()[0]
            print(f"[Reader] Найдено записей: {count}")
            time.sleep(2)
            count = db.execute(text("SELECT COUNT(*) FROM items WHERE name LIKE 'X%'")).fetchone()[0]
            print(f"[Reader] Теперь записей: {count}")

    def write_operation():
        time.sleep(1)
        with Session() as db:
            print("[Writer] Добавление новой записи")
            db.execute(text("INSERT INTO items (name, price) VALUES ('X2', 200)"))
            db.commit()
            print("[Writer] Новая запись добавлена")

    t1 = threading.Thread(target=read_operation)
    t2 = threading.Thread(target=write_operation)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def demonstrate_serializable_isolation():
    print("\n=== ТЕСТ: СЕРИАЛИЗУЕМАЯ ИЗОЛЯЦИЯ ===\n")

    with Session() as db:
        db.execute(text("DELETE FROM items WHERE name LIKE 'Y%'"))
        db.execute(text("INSERT INTO items (name, price) VALUES ('Y1', 100)"))
        db.commit()
        print("[Setup] Подготовлены тестовые данные Y-серии")

    def read_operation():
        with Session() as db:
            try:
                db.execute(text("BEGIN ISOLATION LEVEL SERIALIZABLE"))
                print("[Reader] Начало (SERIALIZABLE)")
                count = db.execute(text("SELECT COUNT(*) FROM items WHERE name LIKE 'Y%'")).fetchone()[0]
                print(f"[Reader] Начальное количество: {count}")
                time.sleep(2)
                count = db.execute(text("SELECT COUNT(*) FROM items WHERE name LIKE 'Y%'")).fetchone()[0]
                print(f"[Reader] Финальное количество: {count}")
                db.commit()
                print("[Reader] Успешное завершение")
            except Exception as e:
                print(f"[Reader] Ошибка: {e}")
                db.rollback()

    def write_operation():
        time.sleep(1)
        with Session() as db:
            try:
                print("[Writer] Попытка записи")
                db.execute(text("BEGIN ISOLATION LEVEL SERIALIZABLE"))
                db.execute(text("INSERT INTO items (name, price) VALUES ('Y2', 200)"))
                db.commit()
                print("[Writer] Запись успешно добавлена")
            except Exception as e:
                print(f"[Writer] Ошибка: {e}")
                db.rollback()

    t1 = threading.Thread(target=read_operation)
    t2 = threading.Thread(target=write_operation)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def execute_tests():
    print("\n" + "="*50)
    print(" ЗАПУСК ТЕСТОВ УРОВНЕЙ ИЗОЛЯЦИИ ".center(50, '='))
    print("="*50 + "\n")

    prepare_test_environment()

    demonstrate_dirty_read_behavior()
    prepare_test_environment()

    demonstrate_changing_reads()
    prepare_test_environment()

    demonstrate_consistent_reads()
    prepare_test_environment()

    demonstrate_phantom_reads()
    prepare_test_environment()

    demonstrate_serializable_isolation()

if __name__ == "__main__":
    execute_tests()
