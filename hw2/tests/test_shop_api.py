import pytest

@pytest.mark.asyncio
async def test_create_and_get_cart(client, db_pool):
    response = await client.post("/cart/")
    assert response.status_code == 201
    cart_id = response.json()["id"]

    async with db_pool.acquire() as conn:
        cart_in_db = await conn.fetchval("SELECT id FROM cart WHERE id = $1", cart_id)
        assert cart_in_db == cart_id

    response = await client.get(f"/cart/{cart_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cart_id
    assert data["items"] == []
    assert data["price"] == 0.0


@pytest.mark.asyncio
async def test_add_and_get_item(client, db_pool):
    item_data = {"name": "Test Item", "price": 10.5}
    response = await client.post("/item/", json=item_data)
    assert response.status_code == 201
    item_id = response.json()["id"]

    async with db_pool.acquire() as conn:
        item_in_db = await conn.fetchrow("SELECT * FROM item WHERE id = $1", item_id)
        assert item_in_db["name"] == "Test Item"
        assert item_in_db["price"] == 10.5
        assert item_in_db["deleted"] == 0

    response = await client.get(f"/item/{item_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Item"


@pytest.mark.asyncio
async def test_add_item_to_cart(client, db_pool):
    async with db_pool.acquire() as conn:
        cart_id = await conn.fetchval("INSERT INTO cart DEFAULT VALUES RETURNING id")
        item_id = await conn.fetchval(
            "INSERT INTO item (name, price) VALUES ($1, $2) RETURNING id", "Item2", 20.0
        )

    response = await client.post(f"/cart/{cart_id}/add/{item_id}")
    assert response.status_code == 200
    assert "added to cart" in response.json()["message"]

    async with db_pool.acquire() as conn:
        cart_item = await conn.fetchrow(
            "SELECT * FROM cart_item WHERE cart_id = $1 AND item_id = $2", cart_id, item_id
        )
        assert cart_item["quantity"] == 1

    response = await client.post(f"/cart/{cart_id}/add/{item_id}")

    async with db_pool.acquire() as conn:
        cart_item = await conn.fetchrow(
            "SELECT * FROM cart_item WHERE cart_id = $1 AND item_id = $2", cart_id, item_id
        )
        assert cart_item["quantity"] == 2
