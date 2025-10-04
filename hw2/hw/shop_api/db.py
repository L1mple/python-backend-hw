# models.py - Модели данных
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, JSON, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

# Базовый класс для всех моделей
Base = declarative_base()

# === МОДЕЛИ ===

class Item(Base):
    """Модель товара"""
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # Автоинкремент ID
    name = Column(String, nullable=False)                       # Название товара
    price = Column(Float, nullable=False)                       # Цена
    deleted = Column(Boolean, default=False)                    # Флаг удаления

class Cart(Base):
    """Модель корзины"""
    __tablename__ = "carts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # Автоинкремент ID
    items = Column(JSON, default=list)                         # Список товаров как JSON
    price = Column(Float, default=0.0)                         # Общая стоимость

#     def calculate_price(self, items):
#         print(items)
#         # Твоя логика подсчёта
#         return sum(item['price'] * item['quantity'] for item in items)

# @event.listens_for(Cart, 'before_update')
# def recalculate_price(mapper, connection, target):
#     target.price = target.calculate_price(target.items)



# database.py - Настройка подключения к БД
class DatabaseManager:
    def __init__(self, database_url: str = "sqlite:///shop.db"):
        """
        Инициализация менеджера БД
        database_url: строка подключения к БД
        """
        # Создаем движок БД (SQLite файл shop.db)
        self.engine = create_engine(database_url, echo=True)  # echo=True показывает SQL запросы
        
        # Создаем фабрику сессий
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Создаем все таблицы
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Получить новую сессию БД"""
        return self.SessionLocal()