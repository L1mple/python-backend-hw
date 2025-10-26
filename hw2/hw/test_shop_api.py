from http import HTTPStatus
from typing import Any, AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from faker import Faker
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from shop_api.main import app, get_session
from shop_api.tables import Base

faker = Faker()


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def engine():
    return create_async_engine("postgresql+asyncpg://admin:admin@localhost:5432/testing")


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def client(engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = async_sessionmaker(engine)

    async def get_session_override():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    async with AsyncClient(transport=ASGITransport(app), base_url="http:///") as async_client:
        yield async_client


@pytest_asyncio.fixture(loop_scope="session")
async def existing_empty_cart_id(client: TestClient) -> int:
    return (await client.post("/cart")).json()["id"]


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def existing_items(client: TestClient) -> list[int]:
    items = [
        {
            "name": f"Тестовый товар {i}",
            "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0),
        }
        for i in range(10)
    ]

    return [(await client.post("/item", json=item)).json()["id"] for item in items]


@pytest_asyncio.fixture(loop_scope="session", scope="session", autouse=True)
async def existing_not_empty_carts(client: TestClient, existing_items: list[int]) -> list[int]:
    carts = []

    for i in range(20):
        cart_id: int = (await client.post("/cart")).json()["id"]
        for item_id in faker.random_elements(existing_items, unique=False, length=i):
            await client.post(f"/cart/{cart_id}/add/{item_id}")

        carts.append(cart_id)

    return carts


@pytest_asyncio.fixture(loop_scope="session")
async def existing_not_empty_cart_id(
    client: TestClient,
    existing_empty_cart_id: int,
    existing_items: list[int],
) -> int:
    for item_id in faker.random_elements(existing_items, unique=False, length=3):
        await client.post(f"/cart/{existing_empty_cart_id}/add/{item_id}")

    return existing_empty_cart_id


@pytest_asyncio.fixture(loop_scope="session")
async def existing_item(client: TestClient) -> dict[str, Any]:
    return (await client.post(
        "/item",
        json={
            "name": f"Тестовый товар {uuid4().hex}",
            "price": faker.pyfloat(min_value=10.0, max_value=100.0),
        },
    )).json()


@pytest_asyncio.fixture(loop_scope="session")
async def deleted_item(client: TestClient, existing_item: dict[str, Any]) -> dict[str, Any]:
    item_id = existing_item["id"]
    await client.delete(f"/item/{item_id}")

    existing_item["deleted"] = True
    return existing_item


@pytest.mark.asyncio(loop_scope="session")
async def test_post_cart(client: TestClient) -> None:
    response = await client.post("/cart")

    assert response.status_code == HTTPStatus.CREATED
    assert "location" in response.headers
    assert "id" in response.json()


@pytest.mark.asyncio(loop_scope="session")
async def test_get_empty_cart(client: TestClient, existing_empty_cart_id: int) -> None:
    response = await client.get(f"/cart/{existing_empty_cart_id}")

    assert response.status_code == HTTPStatus.OK
    response_json = response.json()

    len_items = len(response_json["items"])
    assert len_items == 0
    assert response_json["price"] == 0.0


@pytest.mark.asyncio(loop_scope="session")
async def test_get_not_empty_cart(client: TestClient, existing_not_empty_cart_id: int) -> None:
    response = await client.get(f"/cart/{existing_not_empty_cart_id}")

    assert response.status_code == HTTPStatus.OK
    response_json = response.json()

    len_items = len(response_json["items"])
    assert len_items > 0

    price = 0

    for item in response_json["items"]:
        item_id = item["id"]
        price += (await client.get(f"/item/{item_id}")).json()["price"] * item["quantity"]

    assert response_json["price"] == pytest.approx(price, 1e-8)


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
@pytest.mark.asyncio(loop_scope="session")
async def test_get_cart_list(client: TestClient, query: dict[str, Any], status_code: int):
    response = await client.get("/cart", params=query)

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


@pytest.mark.asyncio(loop_scope="session")
async def test_post_item(client: TestClient) -> None:
    item = {"name": "test item", "price": 9.99}
    response = await client.post("/item", json=item)

    assert response.status_code == HTTPStatus.CREATED

    data = response.json()
    assert item["price"] == data["price"]
    assert item["name"] == data["name"]


@pytest.mark.asyncio(loop_scope="session")
async def test_get_item(client: TestClient, existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]

    response = await client.get(f"/item/{item_id}")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == existing_item


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
@pytest.mark.asyncio(loop_scope="session")
async def test_get_item_list(client: TestClient, query: dict[str, Any], status_code: int) -> None:
    response = await client.get("/item", params=query)

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
@pytest.mark.asyncio(loop_scope="session")
async def test_put_item(
    client: TestClient,
    existing_item: dict[str, Any],
    body: dict[str, Any],
    status_code: int,
) -> None:
    item_id = existing_item["id"]
    response = await client.put(f"/item/{item_id}", json=body)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        new_item = existing_item.copy()
        new_item.update(body)
        assert response.json() == new_item


@pytest.mark.parametrize(
    ("body", "status_code"),
    [
        ({}, HTTPStatus.NOT_MODIFIED),
        ({"price": 9.99}, HTTPStatus.NOT_MODIFIED),
        ({"name": "new name", "price": 9.99}, HTTPStatus.NOT_MODIFIED),
    ],
)
@pytest.mark.asyncio(loop_scope="session")
async def test_patch_deleted_item(client: TestClient, deleted_item: dict[str, Any], body: dict[str, Any], status_code: int) -> None:
    item_id = deleted_item["id"]
    response = await client.patch(f"/item/{item_id}", json=body)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        patch_response_body = response.json()

        response = await client.get(f"/item/{item_id}")
        patched_item = response.json()

        assert patched_item == patch_response_body


@pytest.mark.parametrize(
    ("body", "status_code"),
    [
        ({}, HTTPStatus.OK),
        ({"price": 9.99}, HTTPStatus.OK),
        ({"name": "new name", "price": 9.99}, HTTPStatus.OK),
        (
            {"name": "new name", "price": 9.99, "odd": "value"},
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
        (
            {"name": "new name", "price": 9.99, "deleted": True},
            HTTPStatus.UNPROCESSABLE_ENTITY,
        ),
    ],
)
@pytest.mark.asyncio(loop_scope="session")
async def test_patch_item(client: TestClient, existing_item: dict[str, Any], body: dict[str, Any], status_code: int) -> None:
    item_id = existing_item["id"]
    response = await client.patch(f"/item/{item_id}", json=body)

    assert response.status_code == status_code

    if status_code == HTTPStatus.OK:
        patch_response_body = response.json()

        response = await client.get(f"/item/{item_id}")
        patched_item = response.json()

        assert patched_item == patch_response_body


@pytest.mark.asyncio(loop_scope="session")
async def test_delete_item(client: TestClient, existing_item: dict[str, Any]) -> None:
    item_id = existing_item["id"]

    response = await client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK

    response = await client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND

    response = await client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
