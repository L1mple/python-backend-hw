# transaction_demo.py
import threading
import time
from database import Shop
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

class TransactionDemo:
    def __init__(self):
        self.shop = Shop()
        self.engine = self.shop.db.engine
        self.setup_test_data()
    
    def setup_test_data(self):
        """Создаем тестовые данные"""
        session = self.shop.db.get_session()
        try:
            session.execute(text("DELETE FROM cart_items"))
            session.execute(text("DELETE FROM carts"))
            session.execute(text("DELETE FROM items"))
            
            session.execute(text(
                "INSERT INTO items (id, name, price, deleted) VALUES "
                "(1, 'Wardrobe', 200.0, false),"
                "(2, 'Fridge', 1999.58, false),"
                "(3, 'Dyson', 249.00, false)"
            ))
            
            session.execute(text(
                "INSERT INTO carts (id) VALUES (1), (2)"
            ))
            
            session.commit()
        finally:
            session.close()
            
    def demo_dirty_read(self):
        print("Dirty Read (Грязное чтение)")
        print("Сценарий: Админ меняет цену, пользователь видит промежуточное значение")
        
        def admin_transaction():
            """Админ меняет цену товара"""
            session = self.shop.db.get_session()
            try:
                session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
                session.execute(text("BEGIN"))
                
                session.execute(text("UPDATE items SET price = 899.99 WHERE id = 1"))
                print("👨‍💼 Админ: Цена изменена на 899.99 (ЕЩЕ НЕ СОХРАНИЛ)")
                
                time.sleep(3)
                
                session.execute(text("ROLLBACK"))
                print("👨‍💼 Админ: Ой! Откатываю изменения...")
                
            finally:
                session.close()
        
        def user_transaction():
            """Пользователь смотрит цену"""
            time.sleep(1)
            session = self.shop.db.get_session()
            try:
                session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
                session.execute(text("BEGIN"))
                
                result = session.execute(text("SELECT name, price FROM items WHERE id = 1")).fetchone()
                print(f"👤 Пользователь: Ура! iPhone стоит {result[1]} (DIRTY READ!)")
                
                session.execute(text("COMMIT"))
                
            finally:
                session.close()
        
        t1 = threading.Thread(target=admin_transaction)
        t2 = threading.Thread(target=user_transaction)
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        session = self.shop.db.get_session()
        result = session.execute(text("SELECT price FROM items WHERE id = 1")).fetchone()
        print(f"📊 Фактическая цена iPhone: {result[0]}")
        session.close()
        
    def demo_non_repeatable_read(self):
        """Non-Repeatable Read: Цена меняется между двумя чтениями"""
        print("Non-Repeatable Read (Неповторяемое чтение)")
        
        def user_check_price():
            """Пользователь дважды проверяет цену"""
            session = self.shop.db.get_session()
            try:
                session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
                session.execute(text("BEGIN"))
                
                result1 = session.execute(text("SELECT name, price FROM items WHERE id = 2")).fetchone()
                
                time.sleep(2)
                
                result2 = session.execute(text("SELECT name, price FROM items WHERE id = 2")).fetchone()
                print(f"👤 Пользователь: Теперь стоит {result2[1]} (NON-REPEATABLE READ!)")
                
                session.execute(text("COMMIT"))
                
            finally:
                session.close()
        
        def admin_change_price():
            time.sleep(1)
            session = self.shop.db.get_session()
            try:
                session.execute(text("BEGIN"))
                session.execute(text("UPDATE items SET price = 1799.99 WHERE id = 2"))
                session.execute(text("COMMIT"))
            finally:
                session.close()
        
        t1 = threading.Thread(target=user_check_price)
        t2 = threading.Thread(target=admin_change_price)
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
    def demo_phantom_read(self):
        """Phantom Read: Появляются новые товары между чтениями"""
        print("Phantom Read (Фантомное чтение)")
            
        def user_browse_products():
            session = self.shop.db.get_session()
            try:
                session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
                session.execute(text("BEGIN"))
                
                count1 = session.execute(text("SELECT COUNT(*) FROM items WHERE deleted = false")).fetchone()[0]
                
                time.sleep(2)
                
                count2 = session.execute(text("SELECT COUNT(*) FROM items WHERE deleted = false")).fetchone()[0]
                
                session.execute(text("COMMIT"))
                
            finally:
                session.close()
            
        def admin_add_product():
            """Админ добавляет новый товар"""
            time.sleep(1)
            session = self.shop.db.get_session()
            try:
                session.execute(text("BEGIN"))
                session.execute(text("INSERT INTO items (name, price, deleted) VALUES ('iPad Air', 599.99, false)"))
                session.execute(text("COMMIT"))
            finally:
                session.close()
            
            t1 = threading.Thread(target=user_browse_products)
            t2 = threading.Thread(target=admin_add_product)
            
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            
    def run_all_demos(self):
        print("Демонстрация проблем транзакций")
        
        self.demo_dirty_read()
        time.sleep(2)
        
        self.demo_non_repeatable_read()
        time.sleep(2)
        
        self.demo_phantom_read()
        time.sleep(2)
        
        print("Все демонстрации завершены!")

if __name__ == "__main__":
    demo = TransactionDemo()
    demo.run_all_demos()