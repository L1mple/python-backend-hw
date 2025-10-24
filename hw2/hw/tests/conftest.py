"""
Конфигурация pytest и общие фикстуры
"""

import sys
from pathlib import Path

# Добавляем папку shop_api в путь
project_root = Path(__file__).parent.parent
shop_api_path = project_root / "shop_api"
sys.path.insert(0, str(shop_api_path))

import pytest
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Используем in-memory SQLite для тестов
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    """Создаёт тестовый движок БД (один на всю сессию)"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Включаем поддержку внешних ключей в SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    return engine


@pytest.fixture(scope="session")
def setup_tables(test_engine):
    """Создаёт структуру таблиц один раз для всей сессии"""
    import database
    
    # КРИТИЧЕСКИ ВАЖНО: Импортируем модели ПЕРЕД созданием таблиц
    from models import ItemModel, CartModel  # noqa: F401
    
    # Создаём все таблицы
    database.Base.metadata.create_all(bind=test_engine)
    
    yield
    
    # Удаляем таблицы после всех тестов
    database.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def test_db(test_engine, setup_tables) -> Generator[Session, None, None]:
    """
    Создаёт чистую тестовую БД для каждого теста.
    """
    import database
    
    # Создаём сессию
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        # Очищаем таблицы ПЕРЕД закрытием сессии
        try:
            for table in reversed(database.Base.metadata.sorted_tables):
                session.execute(table.delete())
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()  # Закрываем сессию в самом конце


@pytest.fixture(scope="function")
def client(test_db: Session) -> Generator[TestClient, None, None]:
    """
    Создаёт тестовый клиент FastAPI с подменённой БД.
    """
    import database
    import main
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    # Подменяем зависимость
    main.app.dependency_overrides[database.get_db] = override_get_db
    
    # Создаём клиента
    with TestClient(main.app) as test_client:
        yield test_client
    
    # Очищаем подмену
    main.app.dependency_overrides.clear()


# Настройки pytest
def pytest_configure(config):
    """Конфигурация pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )