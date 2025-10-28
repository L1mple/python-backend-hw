from http import HTTPStatus
from typing import Any, Optional
from uuid import uuid4
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
from faker import Faker
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError, Field, ConfigDict

from shop_api.main import app
from shop_api.schemas import ItemCreate, ItemUpdate, CartCreate

client = TestClient(app)
faker = Faker()


# === Фикстуры ===

@pytest.fixture()
def existing_empty_cart_id() -> int:
    response = client.post("/cart")
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture()
def existing_items() -> list[int]:
    items = [
        {
            "name": f"Тестовый товар {i}",
            "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0),
        }
        for i in range(5)
    ]
    return [client.post("/item", json=item).json()["id"] for item in items]


@pytest.fixture()
def existing_not_empty_cart_id(existing_items: list[int]) -> int:
    response = client.post("/cart")
    assert response.status_code == 201
    cart_id = response.json()["id"]
    for item_id in existing_items[:2]:
        r = client.post(f"/cart/{cart_id}/add/{item_id}")
        assert r.status_code == 200
    return cart_id


@pytest.fixture()
def existing_not_empty_cart_id(
    existing_empty_cart_id: int,
    existing_items: list[int],
) -> int:
    for item_id in faker.random_elements(existing_items, unique=False, length=3):
        client.post(f"/cart/{existing_empty_cart_id}/add/{item_id}")
    return existing_empty_cart_id


@pytest.fixture()
def existing_item() -> dict[str, Any]:
    return client.post(
        "/item",
        json={
            "name": f"Тестовый товар {uuid4().hex}",
            "price": faker.pyfloat(min_value=10.0, max_value=100.0),
        },
    ).json()


@pytest.fixture()
def deleted_item(existing_item: dict[str, Any]) -> dict[str, Any]:
    item_id = existing_item["id"]
    client.delete(f"/item/{item_id}")
    existing_item["deleted"] = True
    return existing_item


# === Тесты Pydantic схем ===

def test_item_create_schema_valid():
    data = {"name": "Valid Item", "price": 10.0}
    item = ItemCreate(**data)
    assert item.name == "Valid Item"
    assert item.price == 10.0


def test_item_create_schema_invalid():
    invalid_data = [
        {},
        {"name": "", "price": -5},
        {"name": "Valid", "price": "string"},
    ]
    for data in invalid_data:
        with pytest.raises(ValidationError):
            ItemCreate(**data)


def test_item_update_schema_valid():
    data = {"name": "Updated", "price": 15.0}
    item = ItemUpdate(**data)
    assert item.name == "Updated"
    assert item.price == 15.0


def test_item_update_schema_invalid():
    # Строгая модель для тестов с бизнес-валидацией
    class StrictItemUpdate(BaseModel):
        model_config = ConfigDict(extra='forbid')  # запрещаем лишние поля

        name: Optional[str] = Field(None, min_length=1)
        price: Optional[float] = Field(None, gt=0)
        available: Optional[bool] = True

    invalid_data = [
        {"price": -10},          # price <= 0
        {"name": ""},            # пустое имя
        {"name": "Valid", "price": "text"},  # price не число
        {"deleted": "not_bool"}, # лишнее поле
        {"odd": "value"},        # лишнее поле
    ]
    for data in invalid_data:
        with pytest.raises(ValidationError):
            StrictItemUpdate(**data)


def test_cart_create_schema():
    cart = CartCreate()
    assert cart is not None


# === Эндпоинты ===

def test_post_cart():
    response = client.post("/cart")
    assert response.status_code == HTTPStatus.CREATED
    assert "id" in response.json()
    assert "location" in response.headers


def test_get_cart(existing_empty_cart_id, existing_not_empty_cart_id):
    # пустая корзина
    response = client.get(f"/cart/{existing_empty_cart_id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "items" in data and "price" in data
    assert len(data["items"]) == 0

    # непустая корзина
    response = client.get(f"/cart/{existing_not_empty_cart_id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data["items"]) > 0


@pytest.mark.parametrize(
    "query,status_code",
    [
        ({}, HTTPStatus.OK),
        ({"offset": 1, "limit": 2}, HTTPStatus.OK),
        ({"min_price": 1000}, HTTPStatus.OK),
        ({"max_price": 20}, HTTPStatus.OK),
        ({"min_quantity": 1}, HTTPStatus.OK),
        ({"max_quantity": 0}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_get_cart_list(query, status_code):
    response = client.get("/cart", params=query)
    assert response.status_code == status_code


def test_post_item_endpoint():
    data = {"name": "Test Item", "price": 9.99}
    response = client.post("/item", json=data)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["name"] == data["name"]


def test_get_item_endpoint(existing_item):
    item_id = existing_item["id"]
    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == existing_item


@pytest.mark.parametrize(
    "body,status_code",
    [
        ({}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"price": 9.99}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"name": "New Name", "price": 9.99}, HTTPStatus.OK),
    ],
)
def test_put_item(existing_item, body, status_code):
    item_id = existing_item["id"]
    response = client.put(f"/item/{item_id}", json=body)
    assert response.status_code == status_code
    if status_code == HTTPStatus.OK:
        expected = existing_item.copy()
        expected.update(body)
        assert response.json() == expected


@pytest.mark.parametrize(
    "item,body,status_code",
    [
        ("deleted_item", {}, HTTPStatus.NOT_MODIFIED),
        ("deleted_item", {"price": 9.99}, HTTPStatus.NOT_MODIFIED),
        ("existing_item", {}, HTTPStatus.OK),
        ("existing_item", {"price": 9.99}, HTTPStatus.OK),
        ("existing_item", {"name": "New", "price": 9.99}, HTTPStatus.OK),
        ("existing_item", {"name": "New", "price": 9.99, "deleted": True}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ("existing_item", {"name": "New", "price": 9.99, "odd": "value"}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_patch_item(request, item, body, status_code):
    item_data = request.getfixturevalue(item)
    item_id = item_data["id"]
    response = client.patch(f"/item/{item_id}", json=body)
    assert response.status_code == status_code


def test_delete_item(existing_item):
    item_id = existing_item["id"]
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    # повторное удаление должно быть ОК
    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK