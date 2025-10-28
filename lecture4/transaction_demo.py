import threading
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shop_api.main import Base, ItemDB

def create_engine_with_isolation(isolation_level):
    return create_engine(
        "sqlite:///file:memdb1?mode=memory&cache=shared",
        connect_args={"check_same_thread": False, "uri": True},
        isolation_level=isolation_level
    )

def setup_test_data():
    engine = create_engine("sqlite:///file:memdb1?mode=memory&cache=shared",
                          connect_args={"check_same_thread": False, "uri": True})
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    session.query(ItemDB).delete()
    
    test_item = ItemDB(name="Test Item", price=100.0, deleted=False)
    session.add(test_item)
    session.commit()
    session.close()
    
    print("✅ Тестовые данные созданы: товар с ценой 100₽")

def demo_dirty_read():
    print("\n" + "="*60)
    print("🔍 ДЕМОНСТРАЦИЯ DIRTY READ")
    print("="*60)
    
    engine1 = create_engine_with_isolation("READ UNCOMMITTED")
    engine2 = create_engine_with_isolation("READ UNCOMMITTED")
    
    Session1 = sessionmaker(bind=engine1)
    Session2 = sessionmaker(bind=engine2)
    
    def transaction1():
        print("👤 Пользователь 1: Начинаю изменение цены...")
        session = Session1()
        try:
            item = session.query(ItemDB).first()
            if item:
                print(f"👤 Пользователь 1: Меняю цену с {item.price}₽ на 999₽")
                item.price = 999.0
                session.flush()
                print("👤 Пользователь 1: Изменения отправлены в БД (но не сохранены)")
                time.sleep(3)
                print("👤 Пользователь 1: Передумал! Откатываю изменения...")
                session.rollback()
                print("👤 Пользователь 1: Изменения отменены")
        finally:
            session.close()
    
    def transaction2():
        time.sleep(1)
        print("👤 Пользователь 2: Читаю цену товара...")
        session = Session2()
        try:
            item = session.query(ItemDB).first()
            if item:
                print(f"👤 Пользователь 2: Вижу цену = {item.price}₽")
                print("❌ DIRTY READ! Пользователь 2 увидел незакоммиченные данные!")
        finally:
            session.close()
    
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def demo_non_repeatable_read():
    print("\n" + "="*60)
    print("🔄 ДЕМОНСТРАЦИЯ NON-REPEATABLE READ")
    print("="*60)
    print("⚠️  SQLite поддерживает только READ UNCOMMITTED и SERIALIZABLE")
    print("   Используем READ UNCOMMITTED для демонстрации")
    
    engine1 = create_engine_with_isolation("READ UNCOMMITTED")
    engine2 = create_engine_with_isolation("READ UNCOMMITTED")
    
    Session1 = sessionmaker(bind=engine1)
    Session2 = sessionmaker(bind=engine2)
    
    def transaction1():
        time.sleep(1)
        print("👤 Пользователь 1: Меняю цену товара...")
        session = Session1()
        try:
            item = session.query(ItemDB).first()
            if item:
                print(f"👤 Пользователь 1: Меняю цену с {item.price}₽ на 200₽")
                item.price = 200.0
                session.commit()
                print("👤 Пользователь 1: Изменения сохранены!")
        finally:
            session.close()
    
    def transaction2():
        print("👤 Пользователь 2: Читаю цену первый раз...")
        session = Session2()
        try:
            item = session.query(ItemDB).first()
            if item:
                print(f"👤 Пользователь 2: Первое чтение - цена = {item.price}₽")
            
            time.sleep(2)
            
            print("👤 Пользователь 2: Читаю цену второй раз...")
            item = session.query(ItemDB).first()
            if item:
                print(f"👤 Пользователь 2: Второе чтение - цена = {item.price}₽")
                print("❌ NON-REPEATABLE READ! Цена изменилась между чтениями!")
        finally:
            session.close()
    
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t2.start()
    t1.start()
    t1.join()
    t2.join()

def demo_phantom_read():
    print("\n" + "="*60)
    print("👻 ДЕМОНСТРАЦИЯ PHANTOM READ")
    print("="*60)
    print("⚠️  SQLite поддерживает только READ UNCOMMITTED и SERIALIZABLE")
    print("   Используем READ UNCOMMITTED для демонстрации")
    
    engine1 = create_engine_with_isolation("READ UNCOMMITTED")
    engine2 = create_engine_with_isolation("READ UNCOMMITTED")
    
    Session1 = sessionmaker(bind=engine1)
    Session2 = sessionmaker(bind=engine2)
    
    def transaction1():
        time.sleep(1)
        print("👤 Пользователь 1: Добавляю новый товар...")
        session = Session1()
        try:
            new_item = ItemDB(name="Новый товар", price=300.0, deleted=False)
            session.add(new_item)
            session.commit()
            print("👤 Пользователь 1: Новый товар добавлен!")
        finally:
            session.close()
    
    def transaction2():
        print("👤 Пользователь 2: Считаю товары первый раз...")
        session = Session2()
        try:
            count = session.query(ItemDB).count()
            print(f"👤 Пользователь 2: Первый подсчет - {count} товаров")
            
            time.sleep(2)
            
            print("👤 Пользователь 2: Считаю товары второй раз...")
            count = session.query(ItemDB).count()
            print(f"👤 Пользователь 2: Второй подсчет - {count} товаров")
            print("❌ PHANTOM READ! Количество товаров изменилось!")
        finally:
            session.close()
    
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t2.start()
    t1.start()
    t1.join()
    t2.join()

def demo_serializable():
    print("\n" + "="*60)
    print("🔒 ДЕМОНСТРАЦИЯ SERIALIZABLE (РЕШЕНИЕ ПРОБЛЕМ)")
    print("="*60)
    
    engine1 = create_engine_with_isolation("SERIALIZABLE")
    engine2 = create_engine_with_isolation("SERIALIZABLE")
    
    Session1 = sessionmaker(bind=engine1)
    Session2 = sessionmaker(bind=engine2)
    
    def transaction1():
        time.sleep(1)
        print("👤 Пользователь 1: Пытаюсь добавить товар...")
        session = Session1()
        try:
            new_item = ItemDB(name="Безопасный товар", price=400.0, deleted=False)
            session.add(new_item)
            session.commit()
            print("👤 Пользователь 1: Товар добавлен успешно!")
        except Exception as e:
            print(f"👤 Пользователь 1: Ошибка - {e}")
            session.rollback()
        finally:
            session.close()
    
    def transaction2():
        print("👤 Пользователь 2: Считаю товары первый раз...")
        session = Session2()
        try:
            count = session.query(ItemDB).count()
            print(f"👤 Пользователь 2: Первый подсчет - {count} товаров")
            
            time.sleep(2)
            
            print("👤 Пользователь 2: Считаю товары второй раз...")
            count = session.query(ItemDB).count()
            print(f"👤 Пользователь 2: Второй подсчет - {count} товаров")
            print("✅ SERIALIZABLE! Количество товаров не изменилось!")
        except Exception as e:
            print(f"👤 Пользователь 2: Ошибка - {e}")
            session.rollback()
        finally:
            session.close()
    
    t1 = threading.Thread(target=transaction1)
    t2 = threading.Thread(target=transaction2)
    
    t2.start()
    t1.start()
    t1.join()
    t2.join()

def main():
    print("🎯 ДЕМОНСТРАЦИЯ ПРОБЛЕМ ТРАНЗАКЦИЙ")
    print("="*60)
    print("Этот скрипт показывает проблемы, которые могут возникнуть")
    print("когда несколько пользователей одновременно работают с БД")
    print("="*60)
    
    setup_test_data()
    
    demo_dirty_read()
    demo_non_repeatable_read()
    demo_phantom_read()
    demo_serializable()
    
    print("\n" + "="*60)
    print("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
    print("="*60)
    print("Выводы:")
    print("• READ UNCOMMITTED - быстрый, но небезопасный")
    print("• READ COMMITTED - предотвращает Dirty Read")
    print("• REPEATABLE READ - предотвращает Non-Repeatable Read")
    print("• SERIALIZABLE - самый безопасный, но медленный")

if __name__ == "__main__":
    main()
