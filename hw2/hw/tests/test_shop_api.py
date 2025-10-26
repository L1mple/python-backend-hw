from http import HTTPStatus
from typing import Any, AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
import httpx
from faker import Faker
from httpx import AsyncClient

from shop_api.main import app
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from shop_api.core.db import DATABASE_URL

faker = Faker()

@pytest_asyncio.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
def engine():
    return create_async_engine(DATABASE_URL)

@pytest_asyncio.fixture(scope="session")
async def async_session_maker(engine: AsyncEngine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield async_session


@pytest_asyncio.fixture(scope="session")
async def async_client() -> AsyncGenerator:
    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture(autouse=True)
async def clean_db(async_session_maker):
    """Clean database before each test"""
    from sqlalchemy import text
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM cart_items"))
        await session.execute(text("DELETE FROM carts"))
        await session.execute(text("DELETE FROM items"))
        await session.commit()

@pytest_asyncio.fixture()
async def items() -> list[dict]:
    """
    5 Items for basic tests
    """
    return [
        {"name": "Test Item 1", "price": 10.0},
        {"name": "Test Item 2", "price": 20.0},
        {"name": "Test Item 3", "price": 30.0},
        {"name": "Test Item 4", "price": 40.0},
        {"name": "Test Item 5", "price": 50.0},
    ]

@pytest_asyncio.fixture()
async def existing_items(async_client: AsyncClient, items: list[dict]) -> list[int]:
    """Create items in the database and return their IDs"""
    result = []
    for item in items:
        response = await async_client.post("/item", json=item)
        if response.status_code == HTTPStatus.CREATED:
            result.append(response.json()["id"])
    return result

@pytest_asyncio.fixture()
async def existing_empty_cart_id(async_client: AsyncClient) -> int:
    response = await async_client.post("/cart")
    return response.json()["id"]

@pytest_asyncio.fixture()
async def existing_not_empty_cart_id(
    async_client: AsyncClient,
    existing_items: list[int],
) -> int:
    # Create a new cart
    response = await async_client.post("/cart")
    cart_id = response.json()["id"]
    
    # Add an item to it
    for item_id in existing_items[:2]:  # Add first two items
        await async_client.post(f"/cart/{cart_id}/add/{item_id}")
    
    return cart_id

    # Add items to it
    for item_id in faker.random_elements(existing_items, unique=False, length=3):
        await async_client.post(f"/cart/{cart_id}/add/{item_id}")

    return cart_id


@pytest_asyncio.fixture()
async def existing_item(async_client: AsyncClient) -> dict[str, Any]:
    response = await async_client.post(
        "/item",
        json={
            "name": f"Тестовый товар {uuid4().hex}",
            "price": faker.pyfloat(min_value=10.0, max_value=100.0),
        },
    )
    return response.json()


@pytest_asyncio.fixture()
async def deleted_item(async_client: AsyncClient) -> dict[str, Any]:
    # Create a new item
    response = await async_client.post(
        "/item",
        json={
            "name": f"Тестовый товар {uuid4().hex}",
            "price": faker.pyfloat(min_value=10.0, max_value=100.0),
        },
    )
    item = response.json()
    
    # Delete it
    await async_client.delete(f"/item/{item['id']}")
    
    item["deleted"] = True
    return item


@pytest.mark.asyncio
async def test_post_cart(async_client: AsyncClient) -> None:
    response = await async_client.post("/cart")

    assert response.status_code == HTTPStatus.CREATED
    assert "location" in response.headers
    assert "id" in response.json()


@pytest.mark.asyncio
async def test_get_cart(async_client: AsyncClient, existing_empty_cart_id: int, existing_not_empty_cart_id: int) -> None:
    # Test empty cart
    response = await async_client.get(f"/cart/{existing_empty_cart_id}")
    assert response.status_code == HTTPStatus.OK
    response_json = response.json()
    assert len(response_json["items"]) == 0
    assert response_json["price"] == 0.0

    # Test non-empty cart
    response = await async_client.get(f"/cart/{existing_not_empty_cart_id}")
    assert response.status_code == HTTPStatus.OK
    response_json = response.json()
    assert len(response_json["items"]) > 0

    # Verify total price calculation
    price = 0
    for item in response_json["items"]:
        item_id = item["id"]
        item_response = await async_client.get(f"/item/{item_id}")
        price += item_response.json()["price"] * item["quantity"]

    assert response_json["price"] == pytest.approx(price, 1e-8)


@pytest_asyncio.fixture()
async def cart_list_test_setup(async_client: AsyncClient, existing_items: list[int]) -> None:
    """Set up test data for cart list tests"""
    # Create a cart with one item
    response = await async_client.post("/cart")
    cart1_id = response.json()["id"]
    await async_client.post(f"/cart/{cart1_id}/add/{existing_items[0]}")  # Add Item1

    # Create a cart with two items
    response = await async_client.post("/cart")
    cart2_id = response.json()["id"]
    await async_client.post(f"/cart/{cart2_id}/add/{existing_items[1]}")  # Add Item2
    await async_client.post(f"/cart/{cart2_id}/add/{existing_items[1]}")  # Add Item2 again

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
@pytest.mark.asyncio
async def test_get_cart_list(async_client: AsyncClient, cart_list_test_setup, query: dict[str, Any], status_code: int):
    response = await async_client.get("/cart", params=query)

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


@pytest.mark.asyncio
async def test_post_item(async_client: AsyncClient) -> None:
    item = {"name": "test item", "price": 9.99}
    response = await async_client.post("/item", json=item)

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()
    assert item["price"] == data["price"]
    assert item["name"] == data["name"]


@pytest.mark.asyncio
async def test_get_item(async_client: AsyncClient, existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]

    response = await async_client.get(f"/item/{item_id}")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == existing_item


@pytest.mark.parametrize(
    ("query", "status_code"),
    [
        ({"offset": 2, "limit": 5}, HTTPStatus.OK),
        ({"min_price": 5.0}, HTTPStatus.OK),
        ({"max_price": 5.0}, HTTPStatus.OK),
        ({"min_price": 1.0, "max_price": 1000.0}, HTTPStatus.OK),
        ({"show_deleted": True}, HTTPStatus.OK),
        ({"show_deleted": False}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
@pytest.mark.asyncio
async def test_get_item_list(async_client: AsyncClient, query: dict[str, Any], status_code: int) -> None:
    response = await async_client.get("/item", params=query)

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
@pytest.mark.asyncio
async def test_put_item(
    async_client: AsyncClient,
    existing_item: dict[str, Any],
    body: dict[str, Any],
    status_code: int,
) -> None:
    item_id = existing_item["id"]
    response = await async_client.put(f"/item/{item_id}", json=body)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        new_item = existing_item.copy()
        new_item.update(body)
        assert response.json() == new_item


@pytest.mark.parametrize(
    ("item_type", "body", "status_code"),
    [
        ("deleted", {}, HTTPStatus.NOT_MODIFIED),
        ("deleted", {"price": 9.99}, HTTPStatus.NOT_MODIFIED),
        ("deleted", {"name": "new name", "price": 9.99}, HTTPStatus.NOT_MODIFIED),
        ("existing", {}, HTTPStatus.OK),
        ("existing", {"price": 9.99}, HTTPStatus.OK),
        ("existing", {"name": "new name", "price": 9.99}, HTTPStatus.OK),
        (
            "existing",
            {"name": "new name", "price": 9.99, "odd": "value"},
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        (
            "existing",
            {"name": "new name", "price": 9.99, "deleted": True},
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    ],
)
@pytest.mark.asyncio
async def test_patch_item(async_client: AsyncClient, existing_item: dict[str, Any], deleted_item: dict[str, Any], item_type: str, body: dict[str, Any], status_code: int) -> None:
    item = deleted_item if item_type == "deleted" else existing_item
    item_id = item["id"]
    response = await async_client.patch(f"/item/{item_id}", json=body)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        patch_response_body = response.json()

        response = await async_client.get(f"/item/{item_id}")
        patched_item = response.json()

        assert patched_item == patch_response_body


@pytest.mark.asyncio
async def test_delete_item(async_client: AsyncClient, existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]

    response = await async_client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK

    response = await async_client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND

    response = await async_client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_add_to_cart_error_cases(async_client: AsyncClient) -> None:
    # Test adding to non-existent cart
    response = await async_client.post("/cart/99999/add/1")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"] == "Cart not found"

    # Create a cart for testing
    response = await async_client.post("/cart")
    cart_id = response.json()["id"]

    # Test adding non-existent item
    response = await async_client.post(f"/cart/{cart_id}/add/99999")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"] == "Item not found"

    # Create an item and delete it
    response = await async_client.post(
        "/item",
        json={
            "name": "Deleted Item",
            "price": 10.0
        }
    )
    item_id = response.json()["id"]
    await async_client.delete(f"/item/{item_id}")

    # Test adding deleted item
    response = await async_client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"] == "Item not found"

    # Create a new item
    response = await async_client.post(
        "/item",
        json={
            "name": "Test Item",
            "price": 10.0
        }
    )
    item_id = response.json()["id"]

    # Add same item multiple times and verify quantity increases
    response = await async_client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == HTTPStatus.OK

    response = await async_client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == HTTPStatus.OK

    # Check the cart contents
    response = await async_client.get(f"/cart/{cart_id}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["id"] == item_id
    assert item["quantity"] == 2  # Should be 2 since we added it twice


@pytest.mark.asyncio
async def test_item_list_filters(async_client: AsyncClient) -> None:
    # Create items with different prices
    items = [
        {"name": "Cheap Item", "price": 5.0},
        {"name": "Mid Item", "price": 10.0},
        {"name": "Expensive Item", "price": 20.0},
    ]
    created_items = []
    
    for item in items:
        response = await async_client.post("/item", json=item)
        assert response.status_code == HTTPStatus.CREATED
        created_items.append(response.json())

    # Delete one item
    await async_client.delete(f"/item/{created_items[1]['id']}")

    # Test min_price filter
    response = await async_client.get("/item?min_price=15.0")
    assert response.status_code == HTTPStatus.OK
    filtered_items = response.json()
    assert len(filtered_items) == 1
    assert filtered_items[0]["price"] == 20.0

    # Test max_price filter
    response = await async_client.get("/item?max_price=7.0")
    assert response.status_code == HTTPStatus.OK
    filtered_items = response.json()
    assert len(filtered_items) == 1
    assert filtered_items[0]["price"] == 5.0

    # Test price range filter
    response = await async_client.get("/item?min_price=4.0&max_price=15.0")
    assert response.status_code == HTTPStatus.OK
    filtered_items = response.json()
    assert len(filtered_items) == 1
    assert filtered_items[0]["price"] == 5.0

    # Test show_deleted=true
    response = await async_client.get("/item?show_deleted=true")
    assert response.status_code == HTTPStatus.OK
    all_items = response.json()
    assert len(all_items) == 3
    assert any(item["deleted"] for item in all_items)


@pytest.mark.asyncio
async def test_cart_list_filters(async_client: AsyncClient, existing_items: list[int]) -> None:
    # Create three carts with known configurations
    # Cart 1: 1x Item1 (10.0)
    # Cart 2: 2x Item2 (40.0)
    # Cart 3: 1x Item2 + 1x Item3 (50.0)
    
    # Create Cart 1 (10.0, qty=1)
    response = await async_client.post("/cart")
    assert response.status_code == HTTPStatus.CREATED
    cart1_id = response.json()["id"]
    await async_client.post(f"/cart/{cart1_id}/add/{existing_items[0]}")  # Add Item1

    # Create Cart 2 (40.0, qty=2)
    response = await async_client.post("/cart")
    assert response.status_code == HTTPStatus.CREATED
    cart2_id = response.json()["id"]
    await async_client.post(f"/cart/{cart2_id}/add/{existing_items[1]}")  # Add Item2
    await async_client.post(f"/cart/{cart2_id}/add/{existing_items[1]}")  # Add Item2 again

    # Create Cart 3 (50.0, qty=2)
    response = await async_client.post("/cart")
    assert response.status_code == HTTPStatus.CREATED
    cart3_id = response.json()["id"]
    await async_client.post(f"/cart/{cart3_id}/add/{existing_items[1]}")  # Add Item2
    await async_client.post(f"/cart/{cart3_id}/add/{existing_items[2]}")  # Add Item3

    # Test min_price filter (should get Cart 3 only)
    response = await async_client.get("/cart?min_price=45.0")
    assert response.status_code == HTTPStatus.OK
    filtered_carts = response.json()
    assert len(filtered_carts) == 1
    assert filtered_carts[0]["price"] == 50.0

    # Test max_price filter (should get Cart 1 only)
    response = await async_client.get("/cart?max_price=15.0")
    assert response.status_code == HTTPStatus.OK
    filtered_carts = response.json()
    assert len(filtered_carts) == 1
    assert filtered_carts[0]["price"] == 10.0

    # Test min_quantity filter (should get Cart 2 and Cart 3)
    response = await async_client.get("/cart?min_quantity=2")
    assert response.status_code == HTTPStatus.OK
    filtered_carts = response.json()
    assert len(filtered_carts) == 2
    for cart in filtered_carts:
        quantity = sum(item["quantity"] for item in cart["items"])
        assert quantity >= 2

    # Test max_quantity filter (should get Cart 1 only)
    response = await async_client.get("/cart?max_quantity=1")
    assert response.status_code == HTTPStatus.OK
    filtered_carts = response.json()
    assert len(filtered_carts) == 1
    cart = filtered_carts[0]
    assert sum(item["quantity"] for item in cart["items"]) == 1

    # Test price and quantity filters combined
    # Should get Cart 2 only: price >= 35.0 and quantity <= 2
    response = await async_client.get("/cart?min_price=35.0&max_quantity=2")
    assert response.status_code == HTTPStatus.OK
    filtered_carts = response.json()
    assert len(filtered_carts) == 2  # Cart 2 and Cart 3 both match these criteria
    cart = filtered_carts[0]
    assert cart["price"] >= 15.0
    assert sum(item["quantity"] for item in cart["items"]) <= 2