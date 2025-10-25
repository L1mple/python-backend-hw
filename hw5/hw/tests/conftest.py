import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from hw5.hw.shop_api.db.database import CartDB, CartItemDB
from hw5.hw.shop_api.store.services import ItemService
import hw5.hw.shop_api.store.routers
import hw5.hw.shop_api.store.models
from hw5.hw.shop_api.main import app
from hw5.hw.shop_api.db.db_init import Base, get_db
from hw5.hw.shop_api.db.settings import DATABASE_URL
from hw5.hw.shop_api.store.models import ItemCreate

# Тестовая БД
engine = create_engine(
    DATABASE_URL
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session():
    with TestingSessionLocal() as session:
        yield session
        session.rollback()


@pytest.fixture
def client(session):
    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def create_test_items(session):
    service = ItemService(session)

    item1 = service.create_item(ItemCreate(name="Milk", price=79.99))
    item2 = service.create_item(ItemCreate(name="Bread", price=49.99))
    item3 = service.create_item(ItemCreate(name="Cheese", price=199.99))

    return [item1.id, item2.id, item3.id]


@pytest.fixture(scope="function")
def client_override_db(session):
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client(client_override_db):
    return client_override_db


@pytest.fixture
def create_test_carts_with_items(session, create_test_items):
    """Создает несколько корзин с товарами для тестирования фильтрации"""
    # Создаем корзины
    cart1 = CartDB(price=75.0)
    cart2 = CartDB(price=150.0)
    cart3 = CartDB(price=25.0)

    session.add_all([cart1, cart2, cart3])
    session.flush()

    # Добавляем товары в корзины
    cart_item1 = CartItemDB(cart_id=cart1.id, item_id=create_test_items[0], quantity=2)
    cart_item2 = CartItemDB(cart_id=cart2.id, item_id=create_test_items[1], quantity=3)
    cart_item3 = CartItemDB(cart_id=cart3.id, item_id=create_test_items[2], quantity=1)

    session.add_all([cart_item1, cart_item2, cart_item3])
    session.commit()

    return [cart1.id, cart2.id, cart3.id]


@pytest.fixture
def create_test_cart_with_items(session, create_test_items):
    """Создает одну корзину с товарами"""
    cart = CartDB(price=0.0)
    session.add(cart)
    session.flush()

    # Добавляем несколько товаров в корзину
    for i, item_id in enumerate(create_test_items[:2]):
        cart_item = CartItemDB(cart_id=cart.id, item_id=item_id, quantity=i + 1)
        session.add(cart_item)

    session.commit()
    return cart.id