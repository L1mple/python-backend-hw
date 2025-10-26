import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, get_db
import db

# ============= FIXTURES =============

@pytest.fixture(scope="function")
def test_engine():
    """
    Создает тестовый engine для in-memory БД
    """
    # Используем check_same_thread=False для SQLite in-memory
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False},
        echo=False
    )
    db.Base.metadata.create_all(bind=engine)
    yield engine
    db.Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine):
    """
    Создает тестовую сессию БД для каждого теста
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    
    TestingSessionLocal = sessionmaker(bind=connection)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(test_db):
    """
    Создает тестовый клиент FastAPI с тестовой БД
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_item_1(client):
    """
    Создает тестовый товар для использования в других тестах
    """
    response = client.post("/item", json={
        "name": "Тестовый товар",
        "price": 100.0,
        "deleted": False
    })
    return response.json()

@pytest.fixture
def sample_item_2(client):
    """
    Создает тестовый товар для использования в других тестах
    """
    response = client.post("/item", json={
        "name": "Тестовый товар - 2",
        "price": 200.0,
        "deleted": True
    })
    return response.json()


@pytest.fixture
def sample_cart(client):
    """
    Создает тестовую корзину
    """
    response = client.post("/cart")
    return response.json()


# ============= ТЕСТЫ ДЛЯ ITEMS =============

class TestCreateItem:
    """Тесты создания товара"""
    
    def test_create_item_success(self, client):
        """Позитивный тест: создание товара с корректными данными"""
        # Arrange
        item_data = {
            "name": "Молоко",
            "price": 99.99,
            "deleted": False
        }
        
        # Act
        response = client.post("/item", json=item_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Молоко"
        assert data["price"] == 99.99
    
    def test_create_item_without_deleted(self, client):
        """Тест: deleted по умолчанию False"""
        response = client.post("/item", json={
            "name": "Хлеб",
            "price": 50.0
        })
        
        assert response.status_code == 201
        # Проверяем через GET что deleted = False
        item_id = response.json()["id"]
        get_response = client.get(f"/item/{item_id}")
        assert get_response.json()["deleted"] == False
    
    def test_create_item_invalid_name(self, client):
        """Негативный тест: пустое имя"""
        response = client.post("/item", json={
            "name": "",
            "price": 100.0
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_create_item_negative_price(self, client):
        """Негативный тест: отрицательная цена"""
        response = client.post("/item", json={
            "name": "Товар",
            "price": -10.0
        })
        
        assert response.status_code == 422
    
    def test_create_item_zero_price(self, client):
        """Граничный тест: цена = 0"""
        response = client.post("/item", json={
            "name": "Товар",
            "price": 0
        })
        
        assert response.status_code == 422  # price должна быть > 0
    
    def test_create_item_extra_fields(self, client):
        """Негативный тест: лишние поля в запросе"""
        response = client.post("/item", json={
            "name": "Товар",
            "price": 100.0,
            "extra_field": "not allowed"
        })
        
        # BaseItem не имеет extra='forbid', поэтому должен пройти
        assert response.status_code == 201


class TestGetItem:
    """Тесты получения товара по ID"""
    
    def test_get_existing_item(self, client, sample_item_1):
        """Позитивный тест: получение существующего товара"""
        item_id = sample_item_1["id"]
        
        response = client.get(f"/item/{item_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == item_id
        assert data["name"] == sample_item_1["name"]
        assert data["price"] == sample_item_1["price"]
    
    def test_get_nonexistent_item(self, client):
        """Негативный тест: товар не найден"""
        response = client.get("/item/99999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetItems:
    """Тесты получения списка товаров с фильтрацией"""
    
    def test_get_items_default_params(self, client):
        """Тест: получение товаров с параметрами по умолчанию"""
        # Создаем несколько товаров
        for i in range(5):
            client.post("/item", json={
                "name": f"Товар {i}",
                "price": 100.0 + i * 10
            })
        
        response = client.get("/item")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5
    
    def test_get_items_with_pagination(self, client):
        """Тест: пагинация"""
        # Создаем 15 товаров
        for i in range(15):
            client.post("/item", json={
                "name": f"Товар {i}",
                "price": 100.0
            })
        
        # Запрос с offset и limit
        response = client.get("/item?offset=5&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
    
    def test_get_items_price_filter(self, client):
        """Тест: фильтрация по цене"""
        # Создаем товары с разными ценами
        client.post("/item", json={"name": "Дешевый", "price": 50.0})
        client.post("/item", json={"name": "Средний", "price": 150.0})
        client.post("/item", json={"name": "Дорогой", "price": 250.0})
        
        response = client.get("/item?min_price=100&max_price=200")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Средний"
    
    def test_get_items_hide_deleted(self, client):
        """Тест: скрытие удаленных товаров по умолчанию"""
        # Создаем обычный и удаленный товар
        client.post("/item", json={"name": "Обычный", "price": 100.0})
        client.post("/item", json={"name": "Удаленный", "price": 100.0, "deleted": True})
        
        response = client.get("/item")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Обычный"
    
    def test_get_items_show_deleted(self, client):
        """Тест: показ удаленных товаров"""
        client.post("/item", json={"name": "Обычный", "price": 100.0})
        client.post("/item", json={"name": "Удаленный", "price": 100.0, "deleted": True})
        
        response = client.get("/item?show_deleted=true")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestUpdateItem:
    """Тесты PUT обновления товара"""
    
    def test_put_item_success(self, client, sample_item_1):
        """Позитивный тест: полное обновление товара"""
        item_id = sample_item_1["id"]
        
        response = client.put(f"/item/{item_id}", json={
            "name": "Обновленный товар",
            "price": 200.0,
            "deleted": False
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Обновленный товар"
        assert data["price"] == 200.0
    
    def test_put_nonexistent_item(self, client):
        """Негативный тест: обновление несуществующего товара"""
        response = client.put("/item/99999", json={
            "name": "Товар",
            "price": 100.0,
            "deleted": False
        })
        
        assert response.status_code == 404


class TestPatchItem:
    """Тесты PATCH частичного обновления"""
    
    def test_patch_item_name(self, client, sample_item_1):
        """Тест: изменение только имени"""
        item_id = sample_item_1["id"]
        
        response = client.patch(f"/item/{item_id}", json={
            "name": "Новое имя"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Новое имя"
        assert data["price"] == sample_item_1["price"]  # Цена не изменилась
    
    def test_patch_item_price(self, client, sample_item_1):
        """Тест: изменение только цены"""
        item_id = sample_item_1["id"]
        
        response = client.patch(f"/item/{item_id}", json={
            "price": 555.55
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 555.55
    
    def test_patch_item_no_changes(self, client, sample_item_1):
        """Тест: PATCH с теми же данными"""
        item_id = sample_item_1["id"]
        
        response = client.patch(f"/item/{item_id}", json={
            "name": sample_item_1["name"],
            "price": sample_item_1["price"]
        })
        
        assert response.status_code == 304  # NOT_MODIFIED
    
    def test_patch_nonexistent_item(self, client):
        """Негативный тест: PATCH несуществующего товара"""
        response = client.patch("/item/99999", json={
            "name": "Новое имя"
        })
        
        assert response.status_code == 304  # В вашем коде NOT_MODIFIED
    
    def test_patch_item_extra_fields_forbidden(self, client, sample_item_1):
        """Тест: PATCH с лишними полями (должны быть запрещены)"""
        item_id = sample_item_1["id"]
        
        response = client.patch(f"/item/{item_id}", json={
            "name": "Новое имя",
            "extra": "field"
        })
        
        assert response.status_code == 422  # extra='forbid' в OptionalBaseItem


class TestDeleteItem:
    """Тесты удаления товара"""
    
    def test_delete_existing_item(self, client, sample_item_1):
        """Позитивный тест: удаление существующего товара"""
        item_id = sample_item_1["id"]
        
        response = client.delete(f"/item/{item_id}")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
        # Проверяем что товар действительно удален
        get_response = client.get(f"/item/{item_id}")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_item(self, client):
        """Тест: удаление несуществующего товара (идемпотентность)"""
        response = client.delete("/item/99999")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ============= ТЕСТЫ ДЛЯ CARTS =============

class TestCreateCart:
    """Тесты создания корзины"""
    
    def test_create_cart_success(self, client):
        """Позитивный тест: создание пустой корзины"""
        response = client.post("/cart")
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        
        # Проверяем заголовок location
        assert "location" in response.headers
        assert response.headers["location"] == f"/cart/{data['id']}"
    
    def test_create_cart_initial_state(self, client):
        """Тест: начальное состояние корзины"""
        response = client.post("/cart")
        cart_id = response.json()["id"]
        
        get_response = client.get(f"/cart/{cart_id}")
        cart = get_response.json()
        
        assert cart["items"] == []
        assert cart["price"] == 0.0


class TestGetCart:
    """Тесты получения корзины"""
    
    def test_get_existing_cart(self, client, sample_cart):
        """Позитивный тест: получение существующей корзины"""
        cart_id = sample_cart["id"]
        
        response = client.get(f"/cart/{cart_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == cart_id
        assert "items" in data
        assert "price" in data


class TestGetCarts:
    """Тесты получения списка корзин с фильтрацией"""
    
    def test_get_carts_default(self, client):
        """Тест: получение корзин по умолчанию"""
        # Создаем несколько корзин
        for _ in range(3):
            client.post("/cart")
        
        response = client.get("/cart")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
    
    def test_get_carts_quantity_filter(self, client, sample_item_1, sample_item_2):
        """Тест: фильтрация по количеству товаров"""
        # Создаем корзины с разным количеством товаров
        cart1_resp = client.post("/cart")
        cart1_id = cart1_resp.json()["id"]
        
        cart2_resp = client.post("/cart")
        cart2_id = cart2_resp.json()["id"]
        
        # Добавляем товары
        client.post(f"/cart/{cart1_id}/add/{sample_item_1['id']}")
        client.post(f"/cart/{cart2_id}/add/{sample_item_1['id']}")
        client.post(f"/cart/{cart2_id}/add/{sample_item_2['id']}")
        
        response = client.get("/cart?min_quantity=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


class TestAddItemToCart:
    """Тесты добавления товара в корзину"""
    
    def test_add_item_to_cart_success(self, client, sample_item_1, sample_cart):
        """Позитивный тест: добавление товара в корзину"""
        cart_id = sample_cart["id"]
        item_id = sample_item_1["id"]
        
        response = client.post(f"/cart/{cart_id}/add/{item_id}")
        
        assert response.status_code == 201
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == item_id
        assert data["items"][0]["quantity"] == 1
        assert data["price"] == sample_item_1["price"]
    
    def test_add_same_item_twice(self, client, sample_item_1, sample_cart):
        """Тест: добавление одного товара дважды (увеличение quantity)"""
        cart_id = sample_cart["id"]
        item_id = sample_item_1["id"]
        
        # Добавляем первый раз
        client.post(f"/cart/{cart_id}/add/{item_id}")
        
        # Добавляем второй раз
        response = client.post(f"/cart/{cart_id}/add/{item_id}")
        
        assert response.status_code == 201
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2
        assert data["price"] == sample_item_1["price"] * 2
    
    def test_add_multiple_different_items(self, client, sample_cart):
        """Тест: добавление разных товаров"""
        cart_id = sample_cart["id"]
        
        # Создаем два товара
        item1 = client.post("/item", json={"name": "Товар 1", "price": 100.0}).json()
        item2 = client.post("/item", json={"name": "Товар 2", "price": 200.0}).json()
        
        # Добавляем в корзину
        client.post(f"/cart/{cart_id}/add/{item1['id']}")
        response = client.post(f"/cart/{cart_id}/add/{item2['id']}")
        
        data = response.json()
        assert len(data["items"]) == 2
        assert data["price"] == 300.0
    
    def test_add_nonexistent_item_to_cart(self, client, sample_cart):
        """Негативный тест: добавление несуществующего товара"""
        cart_id = sample_cart["id"]
        
        response = client.post(f"/cart/{cart_id}/add/99999")
        
        assert response.status_code == 404
        assert "Item" in response.json()["detail"]
    
    def test_add_item_to_nonexistent_cart(self, client, sample_item_1):
        """Негативный тест: добавление в несуществующую корзину"""
        item_id = sample_item_1["id"]
        
        response = client.post(f"/cart/99999/add/{item_id}")
        
        assert response.status_code == 404
        assert "Cart" in response.json()["detail"]


# ============= ИНТЕГРАЦИОННЫЕ ТЕСТЫ =============

class TestIntegration:
    """Комплексные сценарии использования API"""
    
    def test_full_shopping_scenario(self, client):
        """
        Интеграционный тест: полный цикл покупки
        1. Создаем товары
        2. Создаем корзину
        3. Добавляем товары в корзину
        4. Проверяем итоговую цену
        """
        # Создаем товары
        milk = client.post("/item", json={"name": "Молоко", "price": 89.99}).json()
        bread = client.post("/item", json={"name": "Хлеб", "price": 45.50}).json()
        
        # Создаем корзину
        cart = client.post("/cart").json()
        
        # Добавляем товары
        client.post(f"/cart/{cart['id']}/add/{milk['id']}")
        client.post(f"/cart/{cart['id']}/add/{milk['id']}")  # 2 молока
        response = client.post(f"/cart/{cart['id']}/add/{bread['id']}")
        
        # Проверяем результат
        final_cart = response.json()
        expected_price = 89.99 * 2 + 45.50
        assert abs(final_cart["price"] - expected_price) < 0.01  # Сравнение float
        assert len(final_cart["items"]) == 2