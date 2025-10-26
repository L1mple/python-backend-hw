import httpx
from http import HTTPStatus
from uuid import UUID
import pytest


class TestCartAPI:

    @pytest.mark.asyncio
    async def test_create_cart(self, client: httpx.AsyncClient):
        response = await client.post("/carts")
        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert "id" in data
        UUID(data["id"])
        assert response.headers["Location"] == f"/carts/{data['id']}"

    @pytest.mark.asyncio
    async def test_get_cart_not_found(self, client: httpx.AsyncClient):
        fake_id = "12345678-1234-5678-1234-567812345678"
        response = await client.get(f"/carts/{fake_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["msg"] == "Корзина не найдена"

    @pytest.mark.asyncio
    async def test_get_empty_cart(self, client: httpx.AsyncClient):
        cart = (await client.post("/carts")).json()
        cart_id = cart["id"]

        response = await client.get(f"/carts/{cart_id}")
        assert response.status_code == HTTPStatus.OK
        cart_data = response.json()
        assert cart_data["items"] == []
        assert cart_data["price"] == 0.0

    @pytest.mark.asyncio
    async def test_get_cart_with_items(self, client: httpx.AsyncClient):
        item_resp = await client.post("/items", json={"name": "Phone", "price": 500.0})
        item = item_resp.json()
        item_id = item["id"]

        cart_resp = await client.post("/carts")
        cart_id = cart_resp.json()["id"]

        await client.post(f"/carts/{cart_id}/add/{item_id}")

        response = await client.get(f"/carts/{cart_id}")
        assert response.status_code == HTTPStatus.OK
        cart = response.json()
        assert cart["id"] == cart_id
        assert cart["price"] == 500.0
        assert len(cart["items"]) == 1

        cart_item = cart["items"][0]
        assert cart_item["id"] == item_id
        assert cart_item["name"] == "Phone"
        assert cart_item["quantity"] == 1.0
        assert cart_item["available"] is True

    @pytest.mark.asyncio
    async def test_add_item_twice_increases_quantity(self, client: httpx.AsyncClient):
        item = (await client.post("/items", json={"name": "Phone", "price": 500.0})).json()
        item_id = item["id"]

        cart = (await client.post("/carts")).json()
        cart_id = cart["id"]

        await client.post(f"/carts/{cart_id}/add/{item_id}")
        await client.post(f"/carts/{cart_id}/add/{item_id}")

        response = await client.get(f"/carts/{cart_id}")
        cart_data = response.json()
        assert len(cart_data["items"]) == 1
        assert cart_data["items"][0]["quantity"] == 2.0
        assert cart_data["price"] == 1000.0

    @pytest.mark.asyncio
    async def test_list_carts_with_min_price(self, client: httpx.AsyncClient):
        cheap = (await client.post("/items", json={"name": "Cheap", "price": 10.0})).json()
        expensive = (await client.post("/items", json={"name": "Expensive", "price": 200.0})).json()

        cart1 = (await client.post("/carts")).json()
        await client.post(f"/carts/{cart1['id']}/add/{cheap['id']}")

        cart2 = (await client.post("/carts")).json()
        await client.post(f"/carts/{cart2['id']}/add/{expensive['id']}")

        response = await client.get("/carts", params={"min_price": 100.0})
        carts = response.json()
        assert len(carts) == 1
        assert carts[0]["id"] == cart2["id"]
        assert carts[0]["price"] == 200.0

    @pytest.mark.asyncio
    async def test_list_carts_with_max_price(self, client: httpx.AsyncClient):
        cheap = (await client.post("/items", json={"name": "Cheap", "price": 10.0})).json()
        expensive = (await client.post("/items", json={"name": "Expensive", "price": 200.0})).json()

        cart1 = (await client.post("/carts")).json()
        await client.post(f"/carts/{cart1['id']}/add/{cheap['id']}")

        cart2 = (await client.post("/carts")).json()
        await client.post(f"/carts/{cart2['id']}/add/{expensive['id']}")

        response = await client.get("/carts", params={"max_price": 100.0})
        carts = response.json()
        assert len(carts) == 1
        assert carts[0]["id"] == cart1["id"]
        assert carts[0]["price"] == 10.0

        response = await client.get("/carts", params={"max_price": 5.0})
        carts = response.json()
        assert len(carts) == 0

    @pytest.mark.asyncio
    async def test_list_carts_with_max_quantity(self, client: httpx.AsyncClient):
        item = (await client.post("/items", json={"name": "Test", "price": 10.0})).json()

        cart1 = (await client.post("/carts")).json()
        await client.post(f"/carts/{cart1['id']}/add/{item['id']}")

        cart2 = (await client.post("/carts")).json()
        await client.post(f"/carts/{cart2['id']}/add/{item['id']}")
        await client.post(f"/carts/{cart2['id']}/add/{item['id']}")

        resp = await client.get("/carts", params={"max_quantity": 1})
        carts = resp.json()
        assert len(carts) == 1
        assert carts[0]["id"] == cart1["id"]

    @pytest.mark.asyncio
    async def test_list_carts_min_quantity_zero(self, client: httpx.AsyncClient):
        empty_cart = (await client.post("/carts")).json()

        item = (await client.post("/items", json={"name": "Test", "price": 5.0})).json()
        filled_cart = (await client.post("/carts")).json()
        await client.post(f"/carts/{filled_cart['id']}/add/{item['id']}")

        resp = await client.get("/carts", params={"min_quantity": 0})
        carts = resp.json()
        assert len(carts) == 2
        cart_ids = {c["id"] for c in carts}
        assert empty_cart["id"] in cart_ids
        assert filled_cart["id"] in cart_ids

    @pytest.mark.asyncio
    async def test_add_item_to_cart_cart_not_found(self, client: httpx.AsyncClient):
        fake_cart_id = "12345678-1234-5678-1234-567812345678"
        item = (await client.post("/items", json={"name": "Test", "price": 1.0})).json()
        response = await client.post(f"/carts/{fake_cart_id}/add/{item['id']}")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["msg"] == "Ничего не найдено"

    @pytest.mark.asyncio
    async def test_add_item_to_cart_item_not_found(self, client: httpx.AsyncClient):
        cart = (await client.post("/carts")).json()
        fake_item_id = "87654321-4321-8765-4321-876543210987"
        response = await client.post(f"/carts/{cart['id']}/add/{fake_item_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["msg"] == "Ничего не найдено"

    @pytest.mark.asyncio
    async def test_add_deleted_item_to_cart(self, client: httpx.AsyncClient):
        item = (await client.post("/items", json={"name": "DeletedItem", "price": 99.0})).json()
        await client.delete(f"/items/{item['id']}")

        cart = (await client.post("/carts")).json()
        response = await client.post(f"/carts/{cart['id']}/add/{item['id']}")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["msg"] == "Ничего не найдено"

    @pytest.mark.asyncio
    async def test_get_cart_with_deleted_item(self, client: httpx.AsyncClient):
        item = (await client.post("/items", json={"name": "ToBeDeleted", "price": 100.0})).json()
        item_id = item["id"]

        cart = (await client.post("/carts")).json()
        cart_id = cart["id"]
        await client.post(f"/carts/{cart_id}/add/{item_id}")

        await client.delete(f"/items/{item_id}")

        response = await client.get(f"/carts/{cart_id}")
        assert response.status_code == HTTPStatus.OK
        cart_data = response.json()
        assert len(cart_data["items"]) == 0

    @pytest.mark.asyncio
    async def test_list_carts_max_quantity_zero(self, client: httpx.AsyncClient):
        empty_cart = (await client.post("/carts")).json()
        item = (await client.post("/items", json={"name": "Test", "price": 10.0})).json()
        filled_cart = (await client.post("/carts")).json()
        await client.post(f"/carts/{filled_cart['id']}/add/{item['id']}")

        resp = await client.get("/carts", params={"max_quantity": 0, "offset": 0, "limit": 10})
        carts = resp.json()
        assert len(carts) == 1
        assert carts[0]["id"] == empty_cart["id"]