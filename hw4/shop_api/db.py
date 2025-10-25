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



# database.py - Настройка подключения к БД
class DatabaseManager:
    def __init__(self, database_url: str = "sqlite:///shop.db"):
        """
        Инициализация менеджера БД
        database_url: строка подключения к БД
        """
        # Создаем движок БД (SQLite файл shop.db)

        # ОРИГИНАЛ
        # self.engine = create_engine(database_url, echo=True)  # echo=True показывает SQL запросы

        # ИСПРАВЛЕНО ДЛЯ ЭКСПЕРИМЕНТА
        self.engine = create_engine(
            database_url, 
            echo=True, # echo=True показывает SQL запросы
            # isolation_level='READ UNCOMMITTED'
            # isolation_level='SERIALIZABLE'
            )  
        
        # Создаем фабрику сессий
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Создаем все таблицы
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Получить новую сессию БД"""
        return self.SessionLocal()

# from sqlalchemy import create_engine, event
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.pool import StaticPool

# class DatabaseManager:
#     def __init__(self, database_url: str = "sqlite:///shop.db"):
#         """
#         Инициализация менеджера БД с поддержкой dirty reads
#         """
#         # Включаем shared cache mode через параметры URI
#         # ?cache=shared включает режим общего кэша
#         database_url_with_cache = database_url + "?cache=shared"
        
#         self.engine = create_engine(
#             database_url_with_cache,
#             echo=True,
#             # Важно: используем StaticPool чтобы соединения использовали общий кэш
#             poolclass=StaticPool,
#             connect_args={
#                 'check_same_thread': False,  # Разрешаем использование из разных потоков
#             }
#         )
        
#         # Включаем read_uncommitted для всех соединений
#         @event.listens_for(self.engine, "connect")
#         def set_sqlite_pragma(dbapi_connection, connection_record):
#             cursor = dbapi_connection.cursor()
#             cursor.execute("PRAGMA read_uncommitted = 1")
#             cursor.close()
        
#         # Создаем фабрику сессий
#         self.SessionLocal = sessionmaker(bind=self.engine)
        
#         # Создаем все таблицы
#         Base.metadata.create_all(self.engine)
    
#     def get_session(self) -> Session:
#         """Получить новую сессию БД"""
#         return self.SessionLocal()