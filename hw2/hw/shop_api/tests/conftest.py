import os
import sys
from typing import Generator
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, grandparent_dir)

from shop_api.database import Base
from shop_api.database.models import User, Product, Order
from shop_api.main import app

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://shop_user:shop_password@localhost:5432/shop_db_test"
)


@pytest.fixture(scope="session")
def engine():
    """Создает тестовый движок базы данных"""
    test_engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """Создает сессию базы данных для каждого теста"""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    """Создает тестовый клиент FastAPI"""
    from shop_api.database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user(db_session) -> User:
    """Создает тестового пользователя"""
    user = User(
        email="test@example.com",
        name="Test User",
        age=25
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_product(db_session) -> Product:
    """Создает тестовый продукт"""
    product = Product(
        name="Test Product",
        price=99.99,
        description="Test description",
        in_stock=True
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def sample_order(db_session, sample_user, sample_product) -> Order:
    """Создает тестовый заказ"""
    order = Order(
        user_id=sample_user.id,
        product_id=sample_product.id,
        quantity=2,
        total_price=199.98,
        status="pending"
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


# Параметризованные фикстуры для различных сценариев
@pytest.fixture
def user_data() -> dict:
    """Тестовые данные пользователя"""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "age": 25
    }


@pytest.fixture
def product_data() -> dict:
    """Тестовые данные продукта"""
    return {
        "name": "Test Product",
        "price": 99.99,
        "description": "Test description",
        "in_stock": True
    }


@pytest.fixture
def order_data(sample_user, sample_product) -> dict:
    """Тестовые данные заказа"""
    return {
        "user_id": sample_user.id,
        "product_id": sample_product.id,
        "quantity": 2,
        "total_price": 199.98,
        "status": "pending"
    }


# Фикстуры для тестирования ошибок
@pytest.fixture
def invalid_user_data() -> dict:
    """Некорректные данные пользователя"""
    return {
        "email": "invalid-email",
        "name": "Test User",
        "age": -5
    }


@pytest.fixture
def invalid_product_data() -> dict:
    """Некорректные данные продукта"""
    return {
        "name": "Test Product",
        "price": -10.00,
        "description": "Test description",
        "in_stock": True
    }


@pytest.fixture
def invalid_order_data() -> dict:
    """Некорректные данные заказа"""
    return {
        "user_id": 99999,
        "product_id": 99999,
        "quantity": 0
    }
