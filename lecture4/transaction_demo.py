"""
Демонстрация уровней изоляции транзакций в SQLite.

Показывает:
- Dirty read при READ UNCOMMITTED
- Отсутствие dirty read при READ COMMITTED  
- Non-repeatable read при READ COMMITTED
- Отсутствие non-repeatable read при REPEATABLE READ
- Phantom reads при REPEATABLE READ
- Отсутствие phantom reads при SERIALIZABLE
"""

import os
import threading
import time
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# SQLAlchemy setup
DATABASE_URL = "sqlite:///./transaction_demo.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)


# Create tables
Base.metadata.create_all(bind=engine)


def create_test_data():
    """Создаём тестовые данные."""
    db = SessionLocal()
    try:
        # Очищаем таблицу
        db.query(Item).delete()
        
        # Добавляем тестовые товары
        items = [
            Item(name="Товар 1", price=100.0),
            Item(name="Товар 2", price=200.0),
            Item(name="Товар 3", price=300.0),
        ]
        for item in items:
            db.add(item)
        db.commit()
        print("✓ Тестовые данные созданы")
    finally:
        db.close()


def demo_dirty_read():
    """Демонстрация dirty read."""
    print("\n=== ДЕМОНСТРАЦИЯ DIRTY READ ===")
    
    def transaction1():
        """Транзакция 1: изменяет цену, но не коммитит."""
        db = SessionLocal()
        try:
            db.execute(text("PRAGMA read_uncommitted = 1"))  # READ UNCOMMITTED
            item = db.query(Item).filter(Item.name == "Товар 1").first()
            print(f"Транзакция 1: читает цену {item.price}")
            
            item.price = 999.0
            print("Транзакция 1: изменяет цену на 999.0 (НЕ КОММИТИТ)")
            
            time.sleep(2)  # Даём время второй транзакции прочитать
            
            db.rollback()  # Откатываем изменения
            print("Транзакция 1: откатывает изменения")
        finally:
            db.close()
    
    def transaction2():
        """Транзакция 2: читает данные во время незакоммиченной транзакции."""
        time.sleep(1)  # Ждём начала первой транзакции
        db = SessionLocal()
        try:
            db.execute(text("PRAGMA read_uncommitted = 1"))  # READ UNCOMMITTED
            item = db.query(Item).filter(Item.name == "Товар 1").first()
            print(f"Транзакция 2: читает цену {item.price} (DIRTY READ!)")
        finally:
            db.close()
    
    # Запускаем транзакции параллельно
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()


def demo_no_dirty_read():
    """Демонстрация отсутствия dirty read при READ COMMITTED."""
    print("\n=== ДЕМОНСТРАЦИЯ ОТСУТСТВИЯ DIRTY READ ===")
    
    def transaction1():
        """Транзакция 1: изменяет цену, но не коммитит."""
        db = SessionLocal()
        try:
            db.execute(text("PRAGMA read_uncommitted = 0"))  # READ COMMITTED
            item = db.query(Item).filter(Item.name == "Товар 2").first()
            print(f"Транзакция 1: читает цену {item.price}")
            
            item.price = 888.0
            print("Транзакция 1: изменяет цену на 888.0 (НЕ КОММИТИТ)")
            
            time.sleep(2)  # Даём время второй транзакции прочитать
            
            db.rollback()  # Откатываем изменения
            print("Транзакция 1: откатывает изменения")
        finally:
            db.close()
    
    def transaction2():
        """Транзакция 2: читает данные во время незакоммиченной транзакции."""
        time.sleep(1)  # Ждём начала первой транзакции
        db = SessionLocal()
        try:
            db.execute(text("PRAGMA read_uncommitted = 0"))  # READ COMMITTED
            item = db.query(Item).filter(Item.name == "Товар 2").first()
            print(f"Транзакция 2: читает цену {item.price} (НЕТ DIRTY READ)")
        finally:
            db.close()
    
    # Запускаем транзакции параллельно
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()


def demo_non_repeatable_read():
    """Демонстрация non-repeatable read."""
    print("\n=== ДЕМОНСТРАЦИЯ NON-REPEATABLE READ ===")
    
    def transaction1():
        """Транзакция 1: читает данные дважды."""
        db = SessionLocal()
        try:
            db.execute(text("PRAGMA read_uncommitted = 0"))  # READ COMMITTED
            item = db.query(Item).filter(Item.name == "Товар 3").first()
            print(f"Транзакция 1: первое чтение цены {item.price}")
            
            time.sleep(2)  # Ждём изменения во второй транзакции
            
            item = db.query(Item).filter(Item.name == "Товар 3").first()
            print(f"Транзакция 1: второе чтение цены {item.price} (NON-REPEATABLE READ!)")
        finally:
            db.close()
    
    def transaction2():
        """Транзакция 2: изменяет данные между чтениями."""
        time.sleep(1)  # Ждём первого чтения
        db = SessionLocal()
        try:
            item = db.query(Item).filter(Item.name == "Товар 3").first()
            item.price = 777.0
            db.commit()
            print("Транзакция 2: изменяет цену на 777.0 и коммитит")
        finally:
            db.close()
    
    # Запускаем транзакции параллельно
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()


def demo_no_non_repeatable_read():
    """Демонстрация отсутствия non-repeatable read при REPEATABLE READ."""
    print("\n=== ДЕМОНСТРАЦИЯ ОТСУТСТВИЯ NON-REPEATABLE READ ===")
    
    def transaction1():
        """Транзакция 1: читает данные дважды."""
        db = SessionLocal()
        try:
            # SQLite не поддерживает REPEATABLE READ напрямую, используем BEGIN IMMEDIATE
            db.execute(text("BEGIN IMMEDIATE"))
            item = db.query(Item).filter(Item.name == "Товар 1").first()
            print(f"Транзакция 1: первое чтение цены {item.price}")
            
            time.sleep(2)  # Ждём изменения во второй транзакции
            
            item = db.query(Item).filter(Item.name == "Товар 1").first()
            print(f"Транзакция 1: второе чтение цены {item.price} (НЕТ NON-REPEATABLE READ)")
            db.commit()
        finally:
            db.close()
    
    def transaction2():
        """Транзакция 2: пытается изменить данные."""
        time.sleep(1)  # Ждём первого чтения
        db = SessionLocal()
        try:
            item = db.query(Item).filter(Item.name == "Товар 1").first()
            item.price = 666.0
            db.commit()
            print("Транзакция 2: изменяет цену на 666.0 и коммитит")
        except Exception as e:
            print(f"Транзакция 2: не может изменить данные - {e}")
        finally:
            db.close()
    
    # Запускаем транзакции параллельно
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()


def demo_phantom_reads():
    """Демонстрация phantom reads."""
    print("\n=== ДЕМОНСТРАЦИЯ PHANTOM READS ===")
    
    def transaction1():
        """Транзакция 1: считает количество товаров дважды."""
        db = SessionLocal()
        try:
            count = db.query(Item).count()
            print(f"Транзакция 1: первое чтение - {count} товаров")
            
            time.sleep(2)  # Ждём добавления во второй транзакции
            
            count = db.query(Item).count()
            print(f"Транзакция 1: второе чтение - {count} товаров (PHANTOM READ!)")
        finally:
            db.close()
    
    def transaction2():
        """Транзакция 2: добавляет новый товар."""
        time.sleep(1)  # Ждём первого чтения
        db = SessionLocal()
        try:
            new_item = Item(name="Новый товар", price=500.0)
            db.add(new_item)
            db.commit()
            print("Транзакция 2: добавляет новый товар и коммитит")
        finally:
            db.close()
    
    # Запускаем транзакции параллельно
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()


def demo_no_phantom_reads():
    """Демонстрация отсутствия phantom reads при SERIALIZABLE."""
    print("\n=== ДЕМОНСТРАЦИЯ ОТСУТСТВИЯ PHANTOM READS ===")
    
    def transaction1():
        """Транзакция 1: считает количество товаров дважды."""
        db = SessionLocal()
        try:
            db.execute(text("BEGIN IMMEDIATE"))
            count = db.query(Item).count()
            print(f"Транзакция 1: первое чтение - {count} товаров")
            
            time.sleep(2)  # Ждём добавления во второй транзакции
            
            count = db.query(Item).count()
            print(f"Транзакция 1: второе чтение - {count} товаров (НЕТ PHANTOM READ)")
            db.commit()
        finally:
            db.close()
    
    def transaction2():
        """Транзакция 2: пытается добавить новый товар."""
        time.sleep(1)  # Ждём первого чтения
        db = SessionLocal()
        try:
            new_item = Item(name="Ещё один товар", price=600.0)
            db.add(new_item)
            db.commit()
            print("Транзакция 2: добавляет новый товар и коммитит")
        except Exception as e:
            print(f"Транзакция 2: не может добавить товар - {e}")
        finally:
            db.close()
    
    # Запускаем транзакции параллельно
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()


def main():
    """Запуск всех демонстраций."""
    print("ДЕМОНСТРАЦИЯ УРОВНЕЙ ИЗОЛЯЦИИ ТРАНЗАКЦИЙ В SQLITE")
    print("=" * 60)
    
    create_test_data()
    
    demo_dirty_read()
    demo_no_dirty_read()
    demo_non_repeatable_read()
    demo_no_non_repeatable_read()
    demo_phantom_reads()
    demo_no_phantom_reads()
    
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    
    # Очистка
    try:
        os.remove("transaction_demo.db")
    except PermissionError:
        print("Файл БД занят, будет удалён при следующем запуске")


if __name__ == "__main__":
    main()
