"""
Fixed comprehensive tests with proper async support
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from http import HTTPStatus
from typing import Any
from uuid import uuid4
from faker import Faker

faker = Faker()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def existing_empty_cart_id(client: AsyncClient) -> int:
    """Create an empty cart for testing"""
    response = await client.post("/cart")
    return response.json()["id"]


@pytest_asyncio.fixture
async def existing_items(client: AsyncClient) -> list[int]:
    """Create test items for testing"""
    items = [
        {
            "name": f"Test Item {i}",
            "price": faker.pyfloat(positive=True, min_value=10.0, max_value=500.0),
        }
        for i in range(10)
    ]
    item_ids = []
    for item in items:
        response = await client.post("/item", json=item)
        item_ids.append(response.json()["id"])
    return item_ids


@pytest_asyncio.fixture
async def existing_not_empty_carts(client: AsyncClient, existing_items: list[int]) -> list[int]:
    """Create carts with items for testing"""
    carts = []
    for i in range(20):
        response = await client.post("/cart")
        cart_id = response.json()["id"]

        for item_id in faker.random_elements(existing_items, unique=False, length=i):
            await client.post(f"/cart/{cart_id}/add/{item_id}")

        carts.append(cart_id)
    return carts


@pytest_asyncio.fixture
async def existing_not_empty_cart_id(
    client: AsyncClient,
    existing_empty_cart_id: int,
    existing_items: list[int],
) -> int:
    """Create a cart with items for testing"""
    for item_id in faker.random_elements(existing_items, unique=False, length=3):
        await client.post(f"/cart/{existing_empty_cart_id}/add/{item_id}")
    return existing_empty_cart_id


@pytest_asyncio.fixture
async def existing_item(client: AsyncClient) -> dict[str, Any]:
    """Create a single test item"""
    response = await client.post(
        "/item",
        json={
            "name": f"Test Item {uuid4().hex}",
            "price": faker.pyfloat(min_value=10.0, max_value=100.0),
        },
    )
    return response.json()


@pytest_asyncio.fixture
async def deleted_item(client: AsyncClient, existing_item: dict[str, Any]) -> dict[str, Any]:
    """Create a deleted item for testing"""
    item_id = existing_item["id"]
    await client.delete(f"/item/{item_id}")
    existing_item["deleted"] = True
    return existing_item


# ============================================================================
# HEALTH & METRICS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test health check endpoint"""
    response = await client.get("/health")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_metrics_endpoint(client: AsyncClient):
    """Test Prometheus metrics endpoint"""
    response = await client.get("/metrics")
    assert response.status_code == HTTPStatus.OK
    assert "http_requests_total" in response.text


# ============================================================================
# CART TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_post_cart(client: AsyncClient):
    """Test cart creation"""
    response = await client.post("/cart")
    assert response.status_code == HTTPStatus.CREATED
    assert "location" in response.headers
    assert "id" in response.json()


@pytest.mark.asyncio
async def test_get_cart_empty(client: AsyncClient, existing_empty_cart_id: int):
    """Test getting empty cart by ID"""
    response = await client.get(f"/cart/{existing_empty_cart_id}")

    assert response.status_code == HTTPStatus.OK
    response_json = response.json()

    assert len(response_json["items"]) == 0
    assert response_json["price"] == 0.0


@pytest.mark.asyncio
async def test_get_cart_not_empty(client: AsyncClient, existing_not_empty_cart_id: int):
    """Test getting non-empty cart by ID"""
    response = await client.get(f"/cart/{existing_not_empty_cart_id}")

    assert response.status_code == HTTPStatus.OK
    response_json = response.json()

    assert len(response_json["items"]) > 0

    price = 0
    for item in response_json["items"]:
        item_id = item["id"]
        item_response = await client.get(f"/item/{item_id}")
        item_price = item_response.json()["price"]
        price += item_price * item["quantity"]
    assert response_json["price"] == pytest.approx(price, 1e-8)


@pytest.mark.asyncio
async def test_get_cart_not_found(client: AsyncClient):
    """Test getting non-existent cart"""
    response = await client.get("/cart/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
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
async def test_get_cart_list(client: AsyncClient, query: dict[str, Any], status_code: int):
    """Test listing carts with various filters"""
    response = await client.get("/cart", params=query)
    assert response.status_code == status_code
    
    if status_code == HTTPStatus.OK:
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_add_item_to_cart(
    client: AsyncClient,
    existing_empty_cart_id: int,
    existing_items: list[int]
):
    """Test adding item to cart"""
    item_id = existing_items[0]
    response = await client.post(f"/cart/{existing_empty_cart_id}/add/{item_id}")
    assert response.status_code == HTTPStatus.OK
    
    cart_response = await client.get(f"/cart/{existing_empty_cart_id}")
    cart = cart_response.json()
    assert len(cart["items"]) == 1
    assert cart["items"][0]["id"] == item_id
    assert cart["items"][0]["quantity"] == 1


@pytest.mark.asyncio
async def test_add_item_to_cart_increment_quantity(
    client: AsyncClient,
    existing_empty_cart_id: int,
    existing_items: list[int]
):
    """Test that adding same item increments quantity"""
    item_id = existing_items[0]
    
    await client.post(f"/cart/{existing_empty_cart_id}/add/{item_id}")
    await client.post(f"/cart/{existing_empty_cart_id}/add/{item_id}")
    
    cart_response = await client.get(f"/cart/{existing_empty_cart_id}")
    cart = cart_response.json()
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 2


@pytest.mark.asyncio
async def test_add_item_to_nonexistent_cart(client: AsyncClient, existing_items: list[int]):
    """Test adding item to non-existent cart"""
    response = await client.post(f"/cart/999999/add/{existing_items[0]}")
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_add_nonexistent_item_to_cart(client: AsyncClient, existing_empty_cart_id: int):
    """Test adding non-existent item to cart"""
    response = await client.post(f"/cart/{existing_empty_cart_id}/add/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


# ============================================================================
# ITEM TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_post_item(client: AsyncClient):
    """Test item creation"""
    item = {"name": "test item", "price": 9.99}
    response = await client.post("/item", json=item)
    
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert item["price"] == data["price"]
    assert item["name"] == data["name"]
    assert data["deleted"] is False


@pytest.mark.asyncio
async def test_post_item_invalid_price(client: AsyncClient):
    """Test item creation with invalid price"""
    item = {"name": "test item", "price": -9.99}
    response = await client.post("/item", json=item)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_post_item_zero_price(client: AsyncClient):
    """Test item creation with zero price"""
    item = {"name": "test item", "price": 0}
    response = await client.post("/item", json=item)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_get_item(client: AsyncClient, existing_item: dict[str, Any]):
    """Test getting item by ID"""
    item_id = existing_item["id"]
    response = await client.get(f"/item/{item_id}")
    
    assert response.status_code == HTTPStatus.OK
    assert response.json() == existing_item


@pytest.mark.asyncio
async def test_get_item_not_found(client: AsyncClient):
    """Test getting non-existent item"""
    response = await client.get("/item/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_get_deleted_item_not_found(client: AsyncClient, deleted_item: dict[str, Any]):
    """Test that deleted items return 404"""
    item_id = deleted_item["id"]
    response = await client.get(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "status_code"),
    [
        ({"offset": 2, "limit": 5}, HTTPStatus.OK),
        ({"min_price": 5.0}, HTTPStatus.OK),
        ({"max_price": 5.0}, HTTPStatus.OK),
        ({"show_deleted": True}, HTTPStatus.OK),
        ({"show_deleted": False}, HTTPStatus.OK),
        ({"offset": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"limit": 0}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"min_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"max_price": -1}, HTTPStatus.UNPROCESSABLE_ENTITY),
    ],
)
async def test_get_item_list(client: AsyncClient, query: dict[str, Any], status_code: int):
    """Test listing items with various filters"""
    response = await client.get("/item", params=query)
    assert response.status_code == status_code
    
    if status_code == HTTPStatus.OK:
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "status_code"),
    [
        ({}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"price": 9.99}, HTTPStatus.UNPROCESSABLE_ENTITY),
        ({"name": "new name", "price": 9.99}, HTTPStatus.OK),
    ],
)
async def test_put_item(
    client: AsyncClient,
    existing_item: dict[str, Any],
    body: dict[str, Any],
    status_code: int,
):
    """Test full item update"""
    item_id = existing_item["id"]
    response = await client.put(f"/item/{item_id}", json=body)
    
    assert response.status_code == status_code
    
    if status_code == HTTPStatus.OK:
        new_item = existing_item.copy()
        new_item.update(body)
        assert response.json() == new_item


@pytest.mark.asyncio
async def test_put_item_not_found(client: AsyncClient):
    """Test updating non-existent item"""
    response = await client.put("/item/999999", json={"name": "test", "price": 9.99})
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_patch_deleted_item_empty(client: AsyncClient, deleted_item: dict[str, Any]):
    """Test patching deleted item with empty body"""
    item_id = deleted_item["id"]
    response = await client.patch(f"/item/{item_id}", json={})
    assert response.status_code == HTTPStatus.NOT_MODIFIED


@pytest.mark.asyncio
async def test_patch_deleted_item_price(client: AsyncClient, deleted_item: dict[str, Any]):
    """Test patching deleted item price"""
    item_id = deleted_item["id"]
    response = await client.patch(f"/item/{item_id}", json={"price": 9.99})
    assert response.status_code == HTTPStatus.NOT_MODIFIED


@pytest.mark.asyncio
async def test_patch_deleted_item_full(client: AsyncClient, deleted_item: dict[str, Any]):
    """Test patching deleted item with full body"""
    item_id = deleted_item["id"]
    response = await client.patch(f"/item/{item_id}", json={"name": "new name", "price": 9.99})
    assert response.status_code == HTTPStatus.NOT_MODIFIED


@pytest.mark.asyncio
async def test_patch_existing_item_empty(client: AsyncClient, existing_item: dict[str, Any]):
    """Test patching existing item with empty body"""
    item_id = existing_item["id"]
    response = await client.patch(f"/item/{item_id}", json={})
    assert response.status_code == HTTPStatus.OK

    get_response = await client.get(f"/item/{item_id}")
    patched_item = get_response.json()
    assert patched_item == response.json()


@pytest.mark.asyncio
async def test_patch_existing_item_price(client: AsyncClient, existing_item: dict[str, Any]):
    """Test patching existing item price"""
    item_id = existing_item["id"]
    response = await client.patch(f"/item/{item_id}", json={"price": 9.99})
    assert response.status_code == HTTPStatus.OK

    get_response = await client.get(f"/item/{item_id}")
    patched_item = get_response.json()
    assert patched_item == response.json()
    assert patched_item["price"] == 9.99


@pytest.mark.asyncio
async def test_patch_existing_item_name(client: AsyncClient, existing_item: dict[str, Any]):
    """Test patching existing item name"""
    item_id = existing_item["id"]
    response = await client.patch(f"/item/{item_id}", json={"name": "new name"})
    assert response.status_code == HTTPStatus.OK

    get_response = await client.get(f"/item/{item_id}")
    patched_item = get_response.json()
    assert patched_item == response.json()
    assert patched_item["name"] == "new name"


@pytest.mark.asyncio
async def test_patch_existing_item_full(client: AsyncClient, existing_item: dict[str, Any]):
    """Test patching existing item with full body"""
    item_id = existing_item["id"]
    response = await client.patch(f"/item/{item_id}", json={"name": "new name", "price": 9.99})
    assert response.status_code == HTTPStatus.OK

    get_response = await client.get(f"/item/{item_id}")
    patched_item = get_response.json()
    assert patched_item == response.json()


@pytest.mark.asyncio
async def test_patch_existing_item_extra_field(client: AsyncClient, existing_item: dict[str, Any]):
    """Test patching existing item with extra field"""
    item_id = existing_item["id"]
    response = await client.patch(f"/item/{item_id}", json={"name": "new name", "price": 9.99, "odd": "value"})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_patch_existing_item_deleted_field(client: AsyncClient, existing_item: dict[str, Any]):
    """Test patching existing item with deleted field"""
    item_id = existing_item["id"]
    response = await client.patch(f"/item/{item_id}", json={"name": "new name", "price": 9.99, "deleted": True})
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_patch_item_not_found(client: AsyncClient):
    """Test patching non-existent item"""
    response = await client.patch("/item/999999", json={"price": 9.99})
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_delete_item(client: AsyncClient, existing_item: dict[str, Any]):
    """Test item deletion (soft delete)"""
    item_id = existing_item["id"]
    
    response = await client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK
    
    get_response = await client.get(f"/item/{item_id}")
    assert get_response.status_code == HTTPStatus.NOT_FOUND
    
    response = await client.delete(f"/item/{item_id}")
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_delete_item_not_found(client: AsyncClient):
    """Test deleting non-existent item"""
    response = await client.delete("/item/999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_deleted_item_in_cart(
    client: AsyncClient,
    existing_empty_cart_id: int,
    existing_item: dict[str, Any]
):
    """Test that deleted items show as unavailable in cart"""
    item_id = existing_item["id"]
    
    await client.post(f"/cart/{existing_empty_cart_id}/add/{item_id}")
    await client.delete(f"/item/{item_id}")
    
    cart_response = await client.get(f"/cart/{existing_empty_cart_id}")
    cart = cart_response.json()
    assert len(cart["items"]) == 1
    assert cart["items"][0]["available"] is False
    assert cart["price"] == 0.0


# ============================================================================
# WEBSOCKET TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.skip(reason="WebSocket tests require a running server and cannot be tested via AsyncClient")
async def test_websocket_chat():
    """Test websocket chat basic connection - skipped in unit tests"""
    pass


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_complete_shopping_flow(client: AsyncClient):
    """Test a complete shopping flow"""
    item1_response = await client.post("/item", json={"name": "Product 1", "price": 10.0})
    item1 = item1_response.json()
    
    item2_response = await client.post("/item", json={"name": "Product 2", "price": 20.0})
    item2 = item2_response.json()
    
    cart_response = await client.post("/cart")
    cart_id = cart_response.json()["id"]
    
    await client.post(f"/cart/{cart_id}/add/{item1['id']}")
    await client.post(f"/cart/{cart_id}/add/{item1['id']}")
    await client.post(f"/cart/{cart_id}/add/{item2['id']}")
    
    cart_get_response = await client.get(f"/cart/{cart_id}")
    cart = cart_get_response.json()
    assert len(cart["items"]) == 2
    assert cart["items"][0]["quantity"] == 2
    assert cart["items"][1]["quantity"] == 1
    assert cart["price"] == pytest.approx(10.0 * 2 + 20.0)


@pytest.mark.asyncio
async def test_item_lifecycle(client: AsyncClient):
    """Test complete item lifecycle"""
    create_response = await client.post("/item", json={"name": "Lifecycle Test", "price": 50.0})
    item = create_response.json()
    item_id = item["id"]
    
    get_response = await client.get(f"/item/{item_id}")
    fetched = get_response.json()
    assert fetched["name"] == "Lifecycle Test"
    assert fetched["price"] == 50.0
    
    put_response = await client.put(f"/item/{item_id}", json={"name": "Updated Name", "price": 60.0})
    updated = put_response.json()
    assert updated["name"] == "Updated Name"
    assert updated["price"] == 60.0
    
    patch_response = await client.patch(f"/item/{item_id}", json={"price": 70.0})
    patched = patch_response.json()
    assert patched["name"] == "Updated Name"
    assert patched["price"] == 70.0
    
    await client.delete(f"/item/{item_id}")
    final_get_response = await client.get(f"/item/{item_id}")
    assert final_get_response.status_code == HTTPStatus.NOT_FOUND


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.asyncio
async def test_empty_item_name(client: AsyncClient):
    """Test creating item with empty name"""
    response = await client.post("/item", json={"name": "", "price": 10.0})
    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
async def test_very_long_item_name(client: AsyncClient):
    """Test creating item with very long name (should succeed up to 255 chars)"""
    long_name = "A" * 255  # Max length for VARCHAR(255)
    response = await client.post("/item", json={"name": long_name, "price": 10.0})
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["name"] == long_name


@pytest.mark.asyncio
async def test_very_large_price(client: AsyncClient):
    """Test creating item with very large price"""
    response = await client.post("/item", json={"name": "Expensive", "price": 999999999.99})
    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
async def test_pagination_beyond_available_items(client: AsyncClient):
    """Test pagination with offset beyond available items"""
    response = await client.get("/item", params={"offset": 10000, "limit": 10})
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


@pytest.mark.asyncio
async def test_filter_with_impossible_conditions(client: AsyncClient):
    """Test filtering with min_price > max_price"""
    response = await client.get("/item", params={"min_price": 100, "max_price": 50})
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []