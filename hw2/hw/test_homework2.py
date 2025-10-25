from http import HTTPStatus
from typing import Any
from uuid import uuid4

import pytest
from faker import Faker
from fastapi.testclient import TestClient

from shop_api.main import app

client = TestClient(app)
client.__enter__()
faker = Faker()


@pytest.fixture()
def existing_empty_cart_id() -> int:
    return client.post("/cart").json()["id"]


@pytest.fixture(scope="session")
def existing_items() -> list[int]:
    items = [
        {
            "name": f"Тестовый товар {i}",
            "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0),
        }
        for i in range(10)
    ]

    return [client.post("/item", json=item).json()["id"] for item in items]


@pytest.fixture(scope="session", autouse=True)
def existing_not_empty_carts(existing_items: list[int]) -> list[int]:
    carts = []

    for i in range(20):
        cart_id: int = client.post("/cart").json()["id"]
        for item_id in faker.random_elements(existing_items, unique=False, length=i):
            client.post(f"/cart/{cart_id}/add/{item_id}")

        carts.append(cart_id)

    return carts


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


def test_post_cart() -> None:
    response = client.post("/cart")

    assert response.status_code == HTTPStatus.CREATED
    assert "location" in response.headers
    assert "id" in response.json()


@pytest.mark.parametrize(
    ("cart", "not_empty"),
    [
        ("existing_empty_cart_id", False),
        ("existing_not_empty_cart_id", True),
    ],
)
def test_get_cart(request, cart: int, not_empty: bool) -> None:
    cart_id = request.getfixturevalue(cart)

    response = client.get(f"/cart/{cart_id}")

    assert response.status_code == HTTPStatus.OK
    response_json = response.json()

    len_items = len(response_json["items"])
    assert len_items > 0 if not_empty else len_items == 0

    if not_empty:
        price = 0

        for item in response_json["items"]:
            item_id = item["id"]
            price += client.get(f"/item/{item_id}").json()["price"] * item["quantity"]

        assert response_json["price"] == pytest.approx(price, 1e-8)
    else:
        assert response_json["price"] == 0.0


@pytest.mark.parametrize(
    ("query", "status_code"),
    [
        ({}, HTTPStatus.OK),
        ({"offset": 1, "limit": 2}, HTTPStatus.OK),
        ({"min_price": 1000.0}, HTTPStatus.OK),
        ({"max_price": 20.0}, HTTPStatus.OK),
        ({"min_quantity": 1}, HTTPStatus.OK),
        ({"max_quantity": 0}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1.0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_quantity": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_quantity": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_get_cart_list(query: dict[str, Any], status_code: int):
    response = client.get("/cart", params=query)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        data = response.json()

        assert isinstance(data, list)

        if "min_price" in query:
            assert all(item["price"] >= query["min_price"] for item in data)

        if "max_price" in query:
            assert all(item["price"] <= query["max_price"] for item in data)

        quantity = sum(item["quantity"] for cart in data for item in cart["items"])

        if "min_quantity" in query:
            assert quantity >= query["min_quantity"]

        if "max_quantity" in query:
            assert quantity <= query["max_quantity"]


def test_post_item() -> None:
    item = {"name": "test item", "price": 9.99}
    response = client.post("/item", json=item)

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()
    assert item["price"] == data["price"]
    assert item["name"] == data["name"]


def test_get_item(existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]

    response = client.get(f"/item/{item_id}")

    assert response.status_code == HTTPStatus.OK
    result = response.json()
    assert result["id"] == existing_item["id"]
    assert result["name"] == existing_item["name"]
    assert result["deleted"] == existing_item["deleted"]
    # PostgreSQL NUMERIC(10,2) округляет до 2 знаков
    assert abs(result["price"] - existing_item["price"]) < 0.01


@pytest.mark.parametrize(
    ("query", "status_code"),
    [
        ({"offset": 2, "limit": 5}, HTTPStatus.OK),
        ({"min_price": 5.0}, HTTPStatus.OK),
        ({"max_price": 5.0}, HTTPStatus.OK),
        ({"show_deleted": True}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
def test_get_item_list(query: dict[str, Any], status_code: int) -> None:
    response = client.get("/item", params=query)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        data = response.json()

        assert isinstance(data, list)

        if "min_price" in query:
            assert all(item["price"] >= query["min_price"] for item in data)

        if "max_price" in query:
            assert all(item["price"] <= query["max_price"] for item in data)

        if "show_deleted" in query and query["show_deleted"] is False:
            assert all(item["deleted"] is False for item in data)


@pytest.mark.parametrize(
    ("body", "status_code"),
    [
        ({}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"price": 9.99}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"name": "new name", "price": 9.99}, HTTPStatus.OK),
    ],
)
def test_put_item(
    existing_item: dict[str, Any],
    body: dict[str, Any],
    status_code: int,
) -> None:
    item_id = existing_item["id"]
    response = client.put(f"/item/{item_id}", json=body)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        new_item = existing_item.copy()
        new_item.update(body)
        assert response.json() == new_item


@pytest.mark.parametrize(
    ("item", "body", "status_code"),
    [
        ("deleted_item", {}, HTTPStatus.NOT_MODIFIED),
        ("deleted_item", {"price": 9.99}, HTTPStatus.NOT_MODIFIED),
        ("deleted_item", {"name": "new name", "price": 9.99}, HTTPStatus.NOT_MODIFIED),
        ("existing_item", {}, HTTPStatus.OK),
        ("existing_item", {"price": 9.99}, HTTPStatus.OK),
        ("existing_item", {"name": "new name", "price": 9.99}, HTTPStatus.OK),
        (
            "existing_item",
            {"name": "new name", "price": 9.99, "odd": "value"},
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        (
            "existing_item",
            {"name": "new name", "price": 9.99, "deleted": True},
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    ],
)
def test_patch_item(request, item: str, body: dict[str, Any], status_code: int) -> None:
    item_data: dict[str, Any] = request.getfixturevalue(item)
    item_id = item_data["id"]
    response = client.patch(f"/item/{item_id}", json=body)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        patch_response_body = response.json()

        response = client.get(f"/item/{item_id}")
        patched_item = response.json()

        assert patched_item == patch_response_body


def test_delete_item(existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]

    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK

    response = client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND

    response = client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK


def test_add_item_to_cart(
    existing_empty_cart_id: int,
    existing_item: dict[str, Any],
) -> None:
    cart_id = existing_empty_cart_id
    item_id = existing_item["id"]

    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Проверяем, что товар добавлен в корзину
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == HTTPStatus.OK
    cart_data = response.json()
    
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["id"] == item_id
    assert cart_data["items"][0]["quantity"] == 1


def test_add_same_item_to_cart_multiple_times(
    existing_empty_cart_id: int,
    existing_item: dict[str, Any],
) -> None:
    cart_id = existing_empty_cart_id
    item_id = existing_item["id"]

    # Добавляем товар несколько раз
    for _ in range(3):
        response = client.post(f"/cart/{cart_id}/add/{item_id}")
        assert response.status_code == HTTPStatus.NO_CONTENT

    # Проверяем, что количество увеличилось
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == HTTPStatus.OK
    cart_data = response.json()
    
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["quantity"] == 3


def test_add_deleted_item_to_cart(
    existing_empty_cart_id: int,
    deleted_item: dict[str, Any],
) -> None:
    cart_id = existing_empty_cart_id
    item_id = deleted_item["id"]

    # Добавляем удаленный товар в корзину
    response = client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Проверяем, что товар помечен как недоступный
    response = client.get(f"/cart/{cart_id}")
    assert response.status_code == HTTPStatus.OK
    cart_data = response.json()
    
    assert len(cart_data["items"]) == 1
    assert cart_data["items"][0]["available"] is False


def test_add_item_to_nonexistent_cart() -> None:
    nonexistent_cart_id = 999999
    item = client.post(
        "/item",
        json={"name": "test", "price": 10.0},
    ).json()
    item_id = item["id"]

    response = client.post(f"/cart/{nonexistent_cart_id}/add/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_nonexistent_item_to_cart(existing_empty_cart_id: int) -> None:
    cart_id = existing_empty_cart_id
    nonexistent_item_id = 999999

    response = client.post(f"/cart/{cart_id}/add/{nonexistent_item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_nonexistent_cart() -> None:
    nonexistent_cart_id = 999999

    response = client.get(f"/cart/{nonexistent_cart_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_nonexistent_item() -> None:
    nonexistent_item_id = 999999

    response = client.get(f"/item/{nonexistent_item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_put_nonexistent_item() -> None:
    nonexistent_item_id = 999999

    response = client.put(
        f"/item/{nonexistent_item_id}",
        json={"name": "test", "price": 10.0},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_patch_nonexistent_item() -> None:
    nonexistent_item_id = 999999

    response = client.patch(
        f"/item/{nonexistent_item_id}",
        json={"price": 10.0},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_delete_nonexistent_item() -> None:
    nonexistent_item_id = 999999

    response = client.delete(f"/item/{nonexistent_item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_cart_price_calculation(
    existing_empty_cart_id: int,
    existing_items: list[int],
) -> None:
    cart_id = existing_empty_cart_id
    
    # Получаем информацию о товарах
    items_data = []
    for item_id in existing_items[:3]:
        item_response = client.get(f"/item/{item_id}")
        items_data.append(item_response.json())
    
    # Добавляем товары в корзину
    for item in items_data:
        client.post(f"/cart/{cart_id}/add/{item['id']}")
    
    # Проверяем правильность расчета цены
    cart_response = client.get(f"/cart/{cart_id}")
    cart_data = cart_response.json()
    
    expected_price = sum(item["price"] for item in items_data)
    assert cart_data["price"] == pytest.approx(expected_price, 1e-8)


def test_item_availability_in_cart(
    existing_empty_cart_id: int,
    existing_item: dict[str, Any],
) -> None:
    cart_id = existing_empty_cart_id
    item_id = existing_item["id"]
    
    # Добавляем товар в корзину
    client.post(f"/cart/{cart_id}/add/{item_id}")
    
    # Проверяем, что товар доступен
    cart_response = client.get(f"/cart/{cart_id}")
    cart_data = cart_response.json()
    assert cart_data["items"][0]["available"] is True
    
    # Удаляем товар
    client.delete(f"/item/{item_id}")
    
    # Проверяем, что товар теперь недоступен в корзине
    cart_response = client.get(f"/cart/{cart_id}")
    cart_data = cart_response.json()
    assert cart_data["items"][0]["available"] is False


def test_patch_item_with_only_name(existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]
    new_name = "Updated Name Only"
    
    response = client.patch(f"/item/{item_id}", json={"name": new_name})
    assert response.status_code == HTTPStatus.OK
    
    updated_item = response.json()
    assert updated_item["name"] == new_name
    # PostgreSQL NUMERIC(10,2) округляет до 2 знаков
    assert abs(updated_item["price"] - existing_item["price"]) < 0.01


def test_patch_item_with_only_price(existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]
    new_price = 99.99
    
    response = client.patch(f"/item/{item_id}", json={"price": new_price})
    assert response.status_code == HTTPStatus.OK
    
    updated_item = response.json()
    assert updated_item["name"] == existing_item["name"]
    assert updated_item["price"] == new_price


def test_get_carts_with_price_filters(existing_not_empty_carts: list[int]) -> None:
    # Получаем все корзины
    all_carts_response = client.get("/cart", params={"limit": 100})
    all_carts = all_carts_response.json()
    
    if len(all_carts) == 0:
        pytest.skip("No carts available for testing")
    
    # Находим min и max цены
    prices = [cart["price"] for cart in all_carts]
    min_price = min(prices)
    max_price = max(prices)
    mid_price = (min_price + max_price) / 2
    
    # Тестируем фильтр min_price
    response = client.get("/cart", params={"min_price": mid_price, "limit": 100})
    filtered_carts = response.json()
    assert all(cart["price"] >= mid_price for cart in filtered_carts)
    
    # Тестируем фильтр max_price
    response = client.get("/cart", params={"max_price": mid_price, "limit": 100})
    filtered_carts = response.json()
    assert all(cart["price"] <= mid_price for cart in filtered_carts)


def test_get_items_with_price_filters(existing_items: list[int]) -> None:
    # Получаем все товары
    all_items_response = client.get("/item", params={"limit": 100})
    all_items = all_items_response.json()
    
    if len(all_items) == 0:
        pytest.skip("No items available for testing")
    
    # Находим min и max цены
    prices = [item["price"] for item in all_items]
    min_price = min(prices)
    max_price = max(prices)
    mid_price = (min_price + max_price) / 2
    
    # Тестируем фильтр min_price
    response = client.get("/item", params={"min_price": mid_price, "limit": 100})
    filtered_items = response.json()
    assert all(item["price"] >= mid_price for item in filtered_items)
    
    # Тестируем фильтр max_price
    response = client.get("/item", params={"max_price": mid_price, "limit": 100})
    filtered_items = response.json()
    assert all(item["price"] <= mid_price for item in filtered_items)


def test_get_items_show_deleted(existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]
    
    # Подсчитываем общее количество товаров до удаления
    response_before = client.get("/item", params={"show_deleted": True, "limit": 10000})
    total_before = len(response_before.json())
    
    # Удаляем товар
    delete_response = client.delete(f"/item/{item_id}")
    assert delete_response.status_code == HTTPStatus.OK
    
    # Проверяем, что удаленный товар НЕ возвращается при GET по ID (без show_deleted)
    get_response = client.get(f"/item/{item_id}")
    assert get_response.status_code == HTTPStatus.NOT_FOUND
    
    # Проверяем, что количество неудаленных товаров уменьшилось на 1
    response_not_deleted = client.get("/item", params={"show_deleted": False, "limit": 10000})
    not_deleted_items = response_not_deleted.json()
    assert not any(item["id"] == item_id for item in not_deleted_items)
    
    # Проверяем, что с флагом show_deleted=True общее количество НЕ изменилось
    response_with_deleted = client.get("/item", params={"show_deleted": True, "limit": 10000})
    all_items = response_with_deleted.json()
    assert len(all_items) == total_before
    
    # Проверяем, что удаленный товар есть в списке с show_deleted=True
    deleted_item = next((item for item in all_items if item["id"] == item_id), None)
    assert deleted_item is not None
    assert deleted_item["deleted"] is True



def test_offset_and_limit_for_items(existing_items: list[int]) -> None:
    # Тестируем offset и limit
    response = client.get("/item", params={"offset": 0, "limit": 5})
    assert response.status_code == HTTPStatus.OK
    first_batch = response.json()
    assert len(first_batch) <= 5
    
    response = client.get("/item", params={"offset": 5, "limit": 5})
    assert response.status_code == HTTPStatus.OK
    second_batch = response.json()
    
    # Проверяем, что батчи не пересекаются
    if len(first_batch) > 0 and len(second_batch) > 0:
        first_ids = {item["id"] for item in first_batch}
        second_ids = {item["id"] for item in second_batch}
        assert len(first_ids.intersection(second_ids)) == 0


def test_offset_and_limit_for_carts(existing_not_empty_carts: list[int]) -> None:
    # Тестируем offset и limit
    response = client.get("/cart", params={"offset": 0, "limit": 5})
    assert response.status_code == HTTPStatus.OK
    first_batch = response.json()
    assert len(first_batch) <= 5
    
    response = client.get("/cart", params={"offset": 5, "limit": 5})
    assert response.status_code == HTTPStatus.OK
    second_batch = response.json()
    
    # Проверяем, что батчи не пересекаются
    if len(first_batch) > 0 and len(second_batch) > 0:
        first_ids = {cart["id"] for cart in first_batch}
        second_ids = {cart["id"] for cart in second_batch}
        assert len(first_ids.intersection(second_ids)) == 0


def test_post_item_with_invalid_data() -> None:
    # Тест с отрицательной ценой
    response = client.post("/item", json={"name": "test", "price": -10.0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    
    # Тест без имени
    response = client.post("/item", json={"price": 10.0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    
    # Тест без цены
    response = client.post("/item", json={"name": "test"})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_put_item_with_invalid_data(existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]
    
    # Тест с отрицательной ценой
    response = client.put(f"/item/{item_id}", json={"name": "test", "price": -10.0})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_cart_quantity_filters(existing_not_empty_carts: list[int]) -> None:
    # Создаем корзины с известным количеством товаров
    cart1_id = client.post("/cart").json()["id"]
    cart2_id = client.post("/cart").json()["id"]
    
    item = client.post("/item", json={"name": "test", "price": 10.0}).json()
    item_id = item["id"]
    
    # Добавляем 2 товара в первую корзину
    for _ in range(2):
        client.post(f"/cart/{cart1_id}/add/{item_id}")
    
    # Добавляем 5 товаров во вторую корзину
    for _ in range(5):
        client.post(f"/cart/{cart2_id}/add/{item_id}")
    
    # Тестируем min_quantity
    response = client.get("/cart", params={"min_quantity": 3, "limit": 100})
    assert response.status_code == HTTPStatus.OK
    carts = response.json()
    for cart in carts:
        total_qty = sum(item["quantity"] for item in cart["items"])
        assert total_qty >= 3
    
    # Тестируем max_quantity
    response = client.get("/cart", params={"max_quantity": 3, "limit": 100})
    assert response.status_code == HTTPStatus.OK
    carts = response.json()
    for cart in carts:
        total_qty = sum(item["quantity"] for item in cart["items"])
        assert total_qty <= 3

