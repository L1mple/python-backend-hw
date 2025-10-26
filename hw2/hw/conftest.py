import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shop_api.main import Base, app, get_db

# Используем тестовую базу данных PostgreSQL
TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://shop_user:shop_password@localhost:5432/shop_db_test"
)

engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Создание всех таблиц перед запуском тестов"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_database():
    """Очистка данных между тестами"""
    # Очищаем таблицы перед каждым тестом
    db = TestingSessionLocal()
    try:
        # Важно удалять в правильном порядке из-за внешних ключей
        db.execute(Base.metadata.tables['cart_items'].delete())
        db.execute(Base.metadata.tables['carts'].delete())
        db.execute(Base.metadata.tables['items'].delete())
        db.commit()
    finally:
        db.close()
    
    yield
    
    # Очищаем таблицы после каждого теста
    db = TestingSessionLocal()
    try:
        db.execute(Base.metadata.tables['cart_items'].delete())
        db.execute(Base.metadata.tables['carts'].delete())
        db.execute(Base.metadata.tables['items'].delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def override_get_db():
    """Переопределение зависимости get_db для использования тестовой БД"""
    def get_test_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = get_test_db
    yield
    app.dependency_overrides.clear()

