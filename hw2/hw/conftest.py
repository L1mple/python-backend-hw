import os
import pytest
import requests
import time
from http import HTTPStatus
from fastapi.testclient import TestClient
from typing import Generator, List, Dict, Any

# Загружаем тестовые переменные окружения
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '5432'
os.environ['POSTGRES_DB'] = 'shop'
os.environ['POSTGRES_USER'] = 'user'
os.environ['POSTGRES_PASSWORD'] = 'password'
os.environ['REDIS_HOST'] = 'localhost'
os.environ['REDIS_PORT'] = '6379'

from .shop_api.main import app

BASE_URL = "http://localhost:8080"


@pytest.fixture(scope="session", autouse=True)
def wait_for_services():
    """Ожидание готовности сервисов перед запуском тестов"""
    max_retries = 30
    retry_delay = 2

    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/docs", timeout=5)
            if response.status_code == HTTPStatus.OK:
                print("✅ Все сервисы готовы!")
                break
        except Exception as e:
            if i < max_retries - 1:
                print(f"⏳ Ожидаем готовности сервисов... ({i + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                pytest.fail(f"❌ Сервисы не запустились за отведенное время: {e}")


@pytest.fixture(scope="session")
def client():
    """Тестовый клиент для работы с развернутым приложением"""
    return TestClient(app)


@pytest.fixture
def sample_item_data() -> Dict[str, Any]:
    """Фикстура с данными тестового товара"""
    return {
        "name": "Test Product",
        "price": 99.99
    }


@pytest.fixture
def created_item(client: TestClient, sample_item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Фикстура создает товар и возвращает его данные"""
    response = client.post("/item", json=sample_item_data)
    assert response.status_code == HTTPStatus.CREATED
    return response.json()


@pytest.fixture
def created_cart(client: TestClient) -> Dict[str, Any]:
    """Фикстура создает корзину и возвращает ее данные"""
    response = client.post("/cart")
    assert response.status_code == HTTPStatus.CREATED
    return response.json()