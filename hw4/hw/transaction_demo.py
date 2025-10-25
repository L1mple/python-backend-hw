import threading
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import SessionLocal
from shop_api.item.store.models import ItemDB
from shop_api.cart.store.models import CartDB

# Конфигурация базы данных
DATABASE_URL = "postgresql://postgres:password@postgres:5432/shop_db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def setup_test_data():
    """Подготовка тестовых данных используя существующие модели"""
    session = Session()
    try:
        # Очистка тестовых данных
        session.query(ItemDB).filter(ItemDB.name.in_(["TestItem1", "TestItem2", "TestItem3"])).delete()
        session.commit()
        
        # Создание тестовых товаров используя модель ItemDB
        test_items = [
            ItemDB(name="TestItem1", price=100.0, deleted=False),
            ItemDB(name="TestItem2", price=200.0, deleted=False),
            ItemDB(name="TestItem3", price=300.0, deleted=False)
        ]
        
        session.add_all(test_items)
        session.commit()
        print("Тестовые данные созданы с использованием существующих моделей")
        
    except Exception as e:
        session.rollback()
        print(f"Ошибка: {e}")
    finally:
        session.close()

def dirty_read_demo():
    """Демонстрация Dirty Read (грязное чтение)"""
    print("\n" + "="*50)
    print("DIRTY READ - READ UNCOMMITTED")
    print("="*50)
    
    def transaction1():
        """Транзакция, которая изменяет и откатывает"""
        session = Session()
        try:
            print("Транзакция 1: Изменяю цену TestItem1 +50€ (без коммита)")
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
            
            item = session.query(ItemDB).filter(ItemDB.name == "TestItem1").first()
            original_price = item.price
            item.price = item.price + 50
            print(f"Транзакция 1: Изменил цену с {original_price} на {item.price}")
            
            time.sleep(3)  # Пауза для чтения Т2
            print("Транзакция 1: Делаю rollback!")
            session.rollback()
            
        finally:
            session.close()

    def transaction2():
        """Транзакция, которая читает незакоммиченные данные"""
        session = Session()
        try:
            time.sleep(1)  # Ждет изменения Т1
            print("Транзакция 2: Читаю цену TestItem1...")
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
            
            item = session.query(ItemDB).filter(ItemDB.name == "TestItem1").first()
            print(f"Транзакция 2: Вижу {item.price}€ -> DIRTY READ!")
            
        finally:
            session.close()

    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def no_dirty_read_demo():
    """Демонстрация отсутствия Dirty Read с READ COMMITTED"""
    print("\n" + "="*50)
    print("НЕТ DIRTY READ - READ COMMITTED")
    print("="*50)
    
    def transaction1():
        session = Session()
        try:
            print("Транзакция 1: Изменяю цену TestItem1 +50€ (без коммита)")
            
            item = session.query(ItemDB).filter(ItemDB.name == "TestItem1").first()
            original_price = item.price
            item.price = item.price + 50
            print(f"Транзакция 1: Изменил цену с {original_price} на {item.price}")
            
            time.sleep(3)
            print("Транзакция 1: Делаю rollback!")
            session.rollback()
            
        finally:
            session.close()

    def transaction2():
        session = Session()
        try:
            time.sleep(1)
            print("Транзакция 2: Читаю цену TestItem1...")
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            
            item = session.query(ItemDB).filter(ItemDB.name == "TestItem1").first()
            print(f"Транзакция 2: Вижу {item.price}€ -> Чистые данные!")
            
        finally:
            session.close()

    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def non_repeatable_read_demo():
    """Демонстрация Non-Repeatable Read с READ COMMITTED"""
    print("\n" + "="*50)
    print("NON-REPEATABLE READ - READ COMMITTED")
    print("="*50)
    
    def transaction1():
        session = Session()
        try:
            time.sleep(1)
            print("Транзакция 1: Изменяю TestItem2 +100€ и коммит")
            
            item = session.query(ItemDB).filter(ItemDB.name == "TestItem2").first()
            original_price = item.price
            item.price = item.price + 100
            session.commit()
            print(f"Транзакция 1: Изменил цену с {original_price} на {item.price} и закоммитил")
            
        finally:
            session.close()

    def transaction2():
        session = Session()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            
            # Первое чтение
            item = session.query(ItemDB).filter(ItemDB.name == "TestItem2").first()
            price1 = item.price
            print(f"Транзакция 2: Первое чтение -> {price1}€")
            
            time.sleep(2)  # Ждет изменения Т1
            
            # Второе чтение
            session.expire_all()  # Сбрасываем кэш
            item = session.query(ItemDB).filter(ItemDB.name == "TestItem2").first()
            price2 = item.price
            print(f"Транзакция 2: Второе чтение -> {price2}€")
            
            if price1 != price2:
                print("NON-REPEATABLE READ обнаружен!")
                
        finally:
            session.close()

    t2 = threading.Thread(target=transaction2)
    t1 = threading.Thread(target=transaction1)
    
    t2.start()
    t1.start()
    t1.join()
    t2.join()

def no_non_repeatable_read_demo():
    """Демонстрация отсутствия Non-Repeatable Read с REPEATABLE READ"""
    print("\n" + "="*50)
    print("НЕТ NON-REPEATABLE READ - REPEATABLE READ")
    print("="*50)
    
    def transaction1():
        session = Session()
        try:
            time.sleep(1)
            print("Транзакция 1: Изменяю TestItem2 +150€ и коммит")
            
            item = session.query(ItemDB).filter(ItemDB.name == "TestItem2").first()
            original_price = item.price
            item.price = item.price + 150
            session.commit()
            print(f"Транзакция 1: Изменил цену с {original_price} на {item.price} и закоммитил")
            
        finally:
            session.close()

    def transaction2():
        session = Session()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            
            # Первое чтение
            item = session.query(ItemDB).filter(ItemDB.name == "TestItem2").first()
            price1 = item.price
            print(f"Транзакция 2: Первое чтение -> {price1}€")
            
            time.sleep(2)  # Ждет изменения Т1
            
            # Второе чтение
            item = session.query(ItemDB).filter(ItemDB.name == "TestItem2").first()
            price2 = item.price
            print(f"Транзакция 2: Второе чтение -> {price2}€")
            
            if price1 == price2:
                print("Нет Non-Repeatable Read с REPEATABLE READ!")
                
        finally:
            session.close()

    t2 = threading.Thread(target=transaction2)
    t1 = threading.Thread(target=transaction1)
    
    t2.start()
    t1.start()
    t1.join()
    t2.join()

def phantom_read_demo():
    """Демонстрация Phantom Read с REPEATABLE READ"""
    print("\n" + "="*50)
    print("PHANTOM READ - REPEATABLE READ")
    print("="*50)
    
    def transaction1():
        session = Session()
        try:
            time.sleep(1)
            print("Транзакция 1: Добавляю новый товар 'PhantomItem'")
            
            new_item = ItemDB(name="PhantomItem", price=400.0, deleted=False)
            session.add(new_item)
            session.commit()
            print("Транзакция 1: Новый товар добавлен и закоммичен!")
            
        finally:
            session.close()

    def transaction2():
        session = Session()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            
            # Первое чтение
            items = session.query(ItemDB).filter(ItemDB.price > 100).all()
            count1 = len(items)
            print(f"Транзакция 2: Первый подсчет -> {count1} товаров")
            
            time.sleep(2)  # Ждет добавления Т1
            
            # Второе чтение
            items = session.query(ItemDB).filter(ItemDB.price > 100).all()
            count2 = len(items)
            print(f"Транзакция 2: Второй подсчет -> {count2} товаров")
            
            if count1 != count2:
                print("PHANTOM READ обнаружен!")
                
        finally:
            session.close()

    t2 = threading.Thread(target=transaction2)
    t1 = threading.Thread(target=transaction1)
    
    t2.start()
    t1.start()
    t1.join()
    t2.join()

def no_phantom_read_demo():
    """Демонстрация отсутствия Phantom Read с SERIALIZABLE"""
    print("\n" + "="*50)
    print("НЕТ PHANTOM READ - SERIALIZABLE")
    print("="*50)
    
    def transaction1():
        session = Session()
        try:
            time.sleep(1)
            print("Транзакция 1: Добавляю новый товар 'SerializableItem'")
            
            new_item = ItemDB(name="SerializableItem", price=500.0, deleted=False)
            session.add(new_item)
            session.commit()
            print("Транзакция 1: Новый товар добавлен и закоммичен!")
            
        finally:
            session.close()

    def transaction2():
        session = Session()
        try:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            
            # Первое чтение
            items = session.query(ItemDB).filter(ItemDB.price > 100).all()
            count1 = len(items)
            print(f"Транзакция 2: Первый подсчет -> {count1} товаров")
            
            time.sleep(2)  # Ждет добавления Т1
            
            # Второе чтение
            items = session.query(ItemDB).filter(ItemDB.price > 100).all()
            count2 = len(items)
            print(f"Транзакция 2: Второй подсчет -> {count2} товаров")
            
            if count1 == count2:
                print("Нет Phantom Read с SERIALIZABLE!")
                
        finally:
            session.close()

    t2 = threading.Thread(target=transaction2)
    t1 = threading.Thread(target=transaction1)
    
    t2.start()
    t1.start()
    t1.join()
    t2.join()

if __name__ == "__main__":
    print("ДЕМОНСТРАЦИЯ ПРОБЛЕМ ТРАНЗАКЦИЙ")
    print("База данных: PostgreSQL с SQLAlchemy")
    print("Используются существующие модели ItemDB")
    
    # Подготовка
    setup_test_data()
    
    # Демонстрации
    dirty_read_demo()               # 1. Dirty Read с READ UNCOMMITTED
    no_dirty_read_demo()            # 2. Нет Dirty Read с READ COMMITTED  
    non_repeatable_read_demo()      # 3. Non-repeatable Read с READ COMMITTED
    no_non_repeatable_read_demo()   # 4. Нет Non-repeatable Read с REPEATABLE READ
    phantom_read_demo()             # 5. Phantom Read с REPEATABLE READ
    no_phantom_read_demo()          # 6. Нет Phantom Read с SERIALIZABLE
    
    print("\n" + "="*50)
    print("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
    print("="*50)