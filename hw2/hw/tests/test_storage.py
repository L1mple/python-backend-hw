from http import HTTPStatus
from typing import List

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker

from shop_api.core.db import DATABASE_URL
from shop_api.core.schemas import ItemCreate, ItemOut, ItemPatch, ItemPut
from shop_api.core.storage import (
    _session,
    get_item_or_404,
    get_item_soft,
    list_items,
    create_item,
    put_item,
    patch_item,
    delete_item,
    create_cart,
    cart_or_404,
    build_cart_view,
    list_carts,
    add_to_cart,
)

@pytest.fixture(scope="session")
def engine():
    return create_async_engine(DATABASE_URL)

@pytest_asyncio.fixture(scope="session")
async def async_session_maker(engine: AsyncEngine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield async_session

@pytest_asyncio.fixture(autouse=True)
async def clean_db(async_session_maker):
    """Clean database before each test"""
    from sqlalchemy import text
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM cart_items"))
        await session.execute(text("DELETE FROM carts"))
        await session.execute(text("DELETE FROM items"))
        await session.commit()

@pytest_asyncio.fixture
async def item_data() -> ItemCreate:
    return ItemCreate(name="Test Item", price=10.0)

@pytest_asyncio.fixture
async def existing_item(item_data: ItemCreate) -> ItemOut:
    return await create_item(item_data)

@pytest_asyncio.fixture
async def deleted_item(item_data: ItemCreate) -> ItemOut:
    item = await create_item(item_data)
    await delete_item(item.id)
    item.deleted = True
    return item

@pytest_asyncio.fixture
async def existing_items() -> List[ItemOut]:
    """Create multiple items with different prices"""
    items = []
    for i, price in enumerate([5.0, 10.0, 20.0, 30.0, 40.0]):
        data = ItemCreate(name=f"Test Item {i}", price=price)
        items.append(await create_item(data))
    return items

@pytest_asyncio.fixture
async def existing_cart() -> int:
    return await create_cart()

@pytest_asyncio.fixture
async def cart_with_items(existing_cart: int, existing_items: List[ItemOut]) -> int:
    """Create a cart and add some items to it"""
    for item in existing_items[:2]:  # Add first two items
        await add_to_cart(existing_cart, item.id)
    return existing_cart

# Test Item Operations
@pytest.mark.asyncio
async def test_session_context():
    async with _session() as session:
        assert isinstance(session, AsyncSession)

@pytest.mark.asyncio
async def test_get_item_or_404(existing_item: ItemOut):
    # Test existing item
    item = await get_item_or_404(existing_item.id)
    assert item.id == existing_item.id
    assert item.name == existing_item.name
    assert item.price == existing_item.price
    assert not item.deleted

    # Test non-existent item
    with pytest.raises(HTTPException) as exc_info:
        await get_item_or_404(999)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND

    # Test deleted item
    await delete_item(existing_item.id)
    with pytest.raises(HTTPException) as exc_info:
        await get_item_or_404(existing_item.id)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND

@pytest.mark.asyncio
async def test_get_item_soft(existing_item: ItemOut, deleted_item: ItemOut):
    # Test existing item
    item = await get_item_soft(existing_item.id)
    assert item is not None
    assert item.id == existing_item.id
    assert not item.deleted

    # Test deleted item
    item = await get_item_soft(deleted_item.id)
    assert item is not None
    assert item.deleted

    # Test non-existent item
    item = await get_item_soft(999)
    assert item is None

@pytest.mark.asyncio
async def test_list_items(existing_items: List[ItemOut]):
    # Test default parameters
    items = await list_items()
    assert len(items) == 5
    assert all(not item.deleted for item in items)

    # Test min_price filter
    items = await list_items(min_price=15.0)
    assert len(items) == 3
    assert all(item.price >= 15.0 for item in items)

    # Test max_price filter
    items = await list_items(max_price=15.0)
    assert len(items) == 2
    assert all(item.price <= 15.0 for item in items)

    # Test price range
    items = await list_items(min_price=10.0, max_price=30.0)
    assert len(items) == 3
    assert all(10.0 <= item.price <= 30.0 for item in items)

    # Test pagination
    items = await list_items(offset=2, limit=2)
    assert len(items) == 2

    # Test show_deleted
    item_id = existing_items[0].id
    await delete_item(item_id)
    
    items = await list_items(show_deleted=False)
    assert len(items) == 4
    assert all(not item.deleted for item in items)

    items = await list_items(show_deleted=True)
    assert len(items) == 5
    assert any(item.deleted for item in items)

@pytest.mark.asyncio
async def test_create_item(item_data: ItemCreate):
    item = await create_item(item_data)
    assert item.name == item_data.name
    assert item.price == item_data.price
    assert not item.deleted
    assert item.id is not None

@pytest.mark.asyncio
async def test_put_item(existing_item: ItemOut):
    # Test successful update
    data = ItemPut(name="Updated Name", price=20.0)
    updated = await put_item(existing_item.id, data)
    assert updated.name == data.name
    assert updated.price == data.price
    assert updated.id == existing_item.id

    # Test non-existent item
    with pytest.raises(HTTPException) as exc_info:
        await put_item(999, data)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND

    # Test deleted item
    await delete_item(existing_item.id)
    with pytest.raises(HTTPException) as exc_info:
        await put_item(existing_item.id, data)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND

@pytest.mark.asyncio
async def test_patch_item(existing_item: ItemOut, deleted_item: ItemOut):
    # Test partial update - only name
    data = ItemPatch(name="New Name")
    updated = await patch_item(existing_item.id, data)
    assert updated.name == "New Name"
    assert updated.price == existing_item.price

    # Test partial update - only price
    data = ItemPatch(price=25.0)
    updated = await patch_item(existing_item.id, data)
    assert updated.name == "New Name"  # Preserved from previous update
    assert updated.price == 25.0

    # Test invalid price (negative prices are caught by Pydantic validation)
    with pytest.raises(Exception) as exc_info:
        await patch_item(existing_item.id, ItemPatch(price=-1.0))
    assert "greater than or equal to 0" in str(exc_info.value)

    # Test non-existent item
    with pytest.raises(HTTPException) as exc_info:
        await patch_item(999, data)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND

    # Test deleted item
    with pytest.raises(HTTPException) as exc_info:
        await patch_item(deleted_item.id, data)
    assert exc_info.value.status_code == HTTPStatus.NOT_MODIFIED

@pytest.mark.asyncio
async def test_delete_item(existing_item: ItemOut):
    # Test successful delete
    result = await delete_item(existing_item.id)
    assert result == {"ok": True}

    # Verify item is marked as deleted
    item = await get_item_soft(existing_item.id)
    assert item is not None
    assert item.deleted

    # Test idempotency - deleting again should work
    result = await delete_item(existing_item.id)
    assert result == {"ok": True}

# Test Cart Operations
@pytest.mark.asyncio
async def test_create_cart():
    cart_id = await create_cart()
    assert cart_id is not None
    assert isinstance(cart_id, int)

@pytest.mark.asyncio
async def test_cart_or_404(existing_cart: int):
    # Test existing cart
    cart = await cart_or_404(existing_cart)
    assert cart.id == existing_cart

    # Test non-existent cart
    with pytest.raises(HTTPException) as exc_info:
        await cart_or_404(999)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND

@pytest.mark.asyncio
async def test_build_cart_view(cart_with_items: int, existing_items: List[ItemOut]):
    # Test cart with items
    cart = await build_cart_view(cart_with_items)
    assert cart.id == cart_with_items
    assert len(cart.items) == 2
    assert cart.price == sum(item.price for item in existing_items[:2])

    # Test empty cart
    empty_cart_id = await create_cart()
    cart = await build_cart_view(empty_cart_id)
    assert cart.id == empty_cart_id
    assert len(cart.items) == 0
    assert cart.price == 0.0

    # Test non-existent cart
    with pytest.raises(HTTPException) as exc_info:
        await build_cart_view(999)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND

@pytest.mark.asyncio
async def test_list_carts(existing_items: List[ItemOut]):
    # Create carts with different configurations
    # Cart 1: 1x Item1 (5.0)
    cart1_id = await create_cart()
    await add_to_cart(cart1_id, existing_items[0].id)

    # Cart 2: 2x Item2 (20.0)
    cart2_id = await create_cart()
    await add_to_cart(cart2_id, existing_items[1].id)
    await add_to_cart(cart2_id, existing_items[1].id)

    # Cart 3: 1x Item2 + 1x Item3 (30.0)
    cart3_id = await create_cart()
    await add_to_cart(cart3_id, existing_items[1].id)
    await add_to_cart(cart3_id, existing_items[2].id)

    # Test default parameters
    carts = await list_carts()
    assert len(carts) == 3

    # Test min_price filter
    carts = await list_carts(min_price=25.0)
    assert len(carts) == 1
    assert carts[0].price == 30.0

    # Test max_price filter
    carts = await list_carts(max_price=15.0)
    assert len(carts) == 1
    assert carts[0].price == 5.0

    # Test min_quantity filter
    carts = await list_carts(min_quantity=2)
    assert len(carts) == 2
    for cart in carts:
        assert sum(item.quantity for item in cart.items) >= 2

    # Test max_quantity filter
    carts = await list_carts(max_quantity=1)
    assert len(carts) == 1
    for cart in carts:
        assert sum(item.quantity for item in cart.items) == 1

    # Test pagination
    carts = await list_carts(offset=1, limit=1)
    assert len(carts) == 1

@pytest.mark.asyncio
async def test_add_to_cart(existing_cart: int, existing_item: ItemOut, deleted_item: ItemOut):
    # Test adding new item
    result = await add_to_cart(existing_cart, existing_item.id)
    assert result == {"ok": True}

    # Verify item was added
    cart = await build_cart_view(existing_cart)
    assert len(cart.items) == 1
    assert cart.items[0].id == existing_item.id
    assert cart.items[0].quantity == 1

    # Test adding same item again (should increment quantity)
    result = await add_to_cart(existing_cart, existing_item.id)
    assert result == {"ok": True}

    cart = await build_cart_view(existing_cart)
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 2

    # Test adding to non-existent cart
    with pytest.raises(HTTPException) as exc_info:
        await add_to_cart(999, existing_item.id)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND

    # Test adding non-existent item
    with pytest.raises(HTTPException) as exc_info:
        await add_to_cart(existing_cart, 999)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND

    # Test adding deleted item
    with pytest.raises(HTTPException) as exc_info:
        await add_to_cart(existing_cart, deleted_item.id)
    assert exc_info.value.status_code == HTTPStatus.NOT_FOUND