import asyncio
import threading
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import Base, engine
import models

# Создаем тестовые данные
def setup_test_data():
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Очищаем и создаем тестовые данные
    db.query(models.CartItem).delete()
    db.query(models.Cart).delete()
    db.query(models.Item).delete()
    
    item1 = models.Item(name="Test Item 1", price=100.0)
    item2 = models.Item(name="Test Item 2", price=200.0)
    db.add_all([item1, item2])
    db.commit()
    
    print("Test data created")
    db.close()

# 1. Dirty Read демонстрация
def demonstrate_dirty_read():
    print("\n=== Dirty Read Demo ===")
    
    # Транзакция 1 (пишет данные)
    def transaction1():
        engine1 = create_engine("sqlite:///./shop.db", connect_args={"check_same_thread": False})
        Session1 = sessionmaker(bind=engine1)
        db1 = Session1()
        
        # Устанавливаем низкий уровень изоляции
        db1.execute(text("PRAGMA read_uncommitted = 1"))
        
        print("Transaction 1: Starting transaction and updating price...")
        item = db1.query(models.Item).filter(models.Item.name == "Test Item 1").first()
        original_price = item.price
        item.price = 999.0  # Изменяем цену
        db1.flush()  # Сохраняем изменения, но не коммитим
        
        print(f"Transaction 1: Changed price from {original_price} to 999.0 (not committed)")
        time.sleep(2)  # Даем время второй транзакции прочитать данные
        
        db1.rollback()  # Откатываем изменения
        print("Transaction 1: Rollback completed")
        db1.close()
    
    # Транзакция 2 (читает данные)
    def transaction2():
        time.sleep(1)  # Ждем пока первая транзакция сделает изменения
        
        engine2 = create_engine("sqlite:///./shop.db", connect_args={"check_same_thread": False})
        Session2 = sessionmaker(bind=engine2)
        db2 = Session2()
        
        # Устанавливаем низкий уровень изоляции
        db2.execute(text("PRAGMA read_uncommitted = 1"))
        
        print("Transaction 2: Reading item price...")
        item = db2.query(models.Item).filter(models.Item.name == "Test Item 1").first()
        print(f"Transaction 2: Read price = {item.price}")
        
        if item.price == 999.0:
            print("DIRTY READ DETECTED! Read uncommitted data!")
        else:
            print("No dirty read occurred")
        
        db2.close()
    
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

# 2. Защита от Dirty Read (READ COMMITTED)
def demonstrate_no_dirty_read():
    print("\n=== No Dirty Read Demo (READ COMMITTED) ===")
    
    def transaction1():
        engine1 = create_engine("sqlite:///./shop.db", connect_args={"check_same_thread": False})
        Session1 = sessionmaker(bind=engine1)
        db1 = Session1()
        
        print("Transaction 1: Starting transaction and updating price...")
        item = db1.query(models.Item).filter(models.Item.name == "Test Item 1").first()
        original_price = item.price
        item.price = 888.0
        db1.flush()
        
        print(f"Transaction 1: Changed price from {original_price} to 888.0 (not committed)")
        time.sleep(2)
        
        db1.rollback()
        print("Transaction 1: Rollback completed")
        db1.close()
    
    def transaction2():
        time.sleep(1)
        
        engine2 = create_engine("sqlite:///./shop.db", connect_args={"check_same_thread": False})
        Session2 = sessionmaker(bind=engine2)
        db2 = Session2()
        
        # SQLite по умолчанию использует SERIALIZABLE, который предотвращает dirty reads
        print("Transaction 2: Reading item price (with default isolation)...")
        item = db2.query(models.Item).filter(models.Item.name == "Test Item 1").first()
        print(f"Transaction 2: Read price = {item.price}")
        
        if item.price == 888.0:
            print("DIRTY READ DETECTED!")
        else:
            print("No dirty read - reading only committed data")
        
        db2.close()
    
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()

# 3. Non-Repeatable Read демонстрация
def demonstrate_non_repeatable_read():
    print("\n=== Non-Repeatable Read Demo ===")
    
    def transaction1():
        time.sleep(1)  # Ждем пока вторая транзакция сделает первый read
        
        engine1 = create_engine("sqlite:///./shop.db", connect_args={"check_same_thread": False})
        Session1 = sessionmaker(bind=engine1)
        db1 = Session1()
        
        print("Transaction 1: Updating item price...")
        item = db1.query(models.Item).filter(models.Item.name == "Test Item 1").first()
        item.price = 777.0
        db1.commit()
        print("Transaction 1: Price updated and committed")
        db1.close()
    
    def transaction2():
        engine2 = create_engine("sqlite:///./shop.db", connect_args={"check_same_thread": False})
        Session2 = sessionmaker(bind=engine2)
        db2 = Session2()
        
        # Первое чтение
        print("Transaction 2: First read...")
        item = db2.query(models.Item).filter(models.Item.name == "Test Item 1").first()
        first_read = item.price
        print(f"Transaction 2: First read price = {first_read}")
        
        time.sleep(2)  # Ждем пока первая транзакция обновит данные
        
        # Второе чтение (в той же транзакции)
        print("Transaction 2: Second read...")
        db2.expire_all()  # Сбрасываем кэш
        item = db2.query(models.Item).filter(models.Item.name == "Test Item 1").first()
        second_read = item.price
        print(f"Transaction 2: Second read price = {second_read}")
        
        if first_read != second_read:
            print("NON-REPEATABLE READ DETECTED! Different values in same transaction!")
        else:
            print("Repeatable reads maintained")
        
        db2.close()
    
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t2.start()
    t1.start()
    
    t1.join()
    t2.join()

# 4. Phantom Read демонстрация
def demonstrate_phantom_read():
    print("\n=== Phantom Read Demo ===")
    
    def transaction1():
        time.sleep(1)  # Ждем пока вторая транзакция сделает первый read
        
        engine1 = create_engine("sqlite:///./shop.db", connect_args={"check_same_thread": False})
        Session1 = sessionmaker(bind=engine1)
        db1 = Session1()
        
        print("Transaction 1: Inserting new item...")
        new_item = models.Item(name="New Phantom Item", price=555.0)
        db1.add(new_item)
        db1.commit()
        print("Transaction 1: New item inserted and committed")
        db1.close()
    
    def transaction2():
        engine2 = create_engine("sqlite:///./shop.db", connect_args={"check_same_thread": False})
        Session2 = sessionmaker(bind=engine2)
        db2 = Session2()
        
        # Первое чтение
        print("Transaction 2: First read of items...")
        items = db2.query(models.Item).filter(models.Item.price > 100).all()
        first_count = len(items)
        print(f"Transaction 2: First read found {first_count} items")
        
        time.sleep(2)  # Ждем пока первая транзакция вставит новые данные
        
        # Второе чтение
        print("Transaction 2: Second read of items...")
        db2.expire_all()  # Сбрасываем кэш
        items = db2.query(models.Item).filter(models.Item.price > 100).all()
        second_count = len(items)
        print(f"Transaction 2: Second read found {second_count} items")
        
        if first_count != second_count:
            print("PHANTOM READ DETECTED! Different number of rows in same transaction!")
        else:
            print("Phantom reads prevented")
        
        db2.close()
    
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t2.start()
    t1.start()
    
    t1.join()
    t2.join()

if __name__ == "__main__":
    print("Setting up test data...")
    setup_test_data()
    
    demonstrate_dirty_read()
    demonstrate_no_dirty_read()
    demonstrate_non_repeatable_read()
    demonstrate_phantom_read()
    
    print("\n=== Demo Complete ===")