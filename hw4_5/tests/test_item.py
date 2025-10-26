import httpx
from http import HTTPStatus
from uuid import UUID, uuid4
import pytest


class TestItemAPI:

    @pytest.mark.asyncio
    async def test_create_item(self, client: httpx.AsyncClient):
        response = await client.post("/items", json={"name": "Laptop", "price": 999.99})
        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        UUID(data["id"])

        response = await client.get(f"/items/{data["id"]}")
        assert response.status_code == HTTPStatus.OK
        response = response.json()
        assert response["name"] == "Laptop"
        assert response["price"] == 999.99
        assert response["deleted"] is False

    @pytest.mark.asyncio
    async def test_get_item_not_found(self, client: httpx.AsyncClient):
        fake_id = "12345678-1234-5678-1234-567812345678"
        response = await client.get(f"/items/{fake_id}")
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["msg"] == "Ничего не найдено"


    @pytest.mark.asyncio
    async def test_list_items_with_min_price(self, client: httpx.AsyncClient):
        await client.post("/items", json={"name": "Cheap", "price": 5.0})
        await client.post("/items", json={"name": "Expensive", "price": 150.0})

        resp = await client.get("/items", params={"min_price": 100.0})
        items = resp.json()
        assert len(items) == 1
        assert all(i["price"] >= 100.0 for i in items)

    @pytest.mark.asyncio
    async def test_list_items_with_max_price(self, client: httpx.AsyncClient):
        await client.post("/items", json={"name": "Cheap", "price": 10.0})
        await client.post("/items", json={"name": "Expensive", "price": 200.0})

        resp = await client.get("/items", params={"max_price": 50.0})
        items = resp.json()
        assert len(items) == 1
        assert items[0]["name"] == "Cheap"

    @pytest.mark.asyncio
    async def test_update_item_full(self, client: httpx.AsyncClient):
        id = uuid4()
        resp = (await client.put(f"/items/{id}", json={"name": "New", "price": 200.0}))
        assert resp.json()["msg"] == "Ничего не найдено"

        item = (await client.post("/items", json={"name": "Old", "price": 100.0})).json()
        item_id = item["id"]
        updated = (await client.put(f"/items/{item_id}", json={"name": "New", "price": 200.0})).json()
        assert updated["name"] == "New"
        assert updated["price"] == 200.0
        assert updated["deleted"] is False

    @pytest.mark.asyncio
    async def test_update_item_partial(self, client: httpx.AsyncClient):

        id = uuid4()
        resp = (await client.patch(f"/items/{id}", json={"price": 150.0}))
        assert resp.json()["msg"] == "Ничего не найдено"

        item = (await client.post("/items", json={"name": "Original", "price": 100.0})).json()
        item_id = item["id"]
        patched = (await client.patch(f"/items/{item_id}", json={"price": 150.0})).json()
        assert patched["name"] == "Original"
        assert patched["price"] == 150.0
        assert patched["deleted"] is False

    @pytest.mark.asyncio
    async def test_soft_delete_item(self, client: httpx.AsyncClient):
        item = (await client.post("/items", json={"name": "ToBeDeleted", "price": 10.0})).json()
        item_id = item["id"]
        assert item["deleted"] is False

        del_resp = await client.delete(f"/items/{item_id}")
        assert del_resp.status_code == HTTPStatus.OK
        deleted_item = del_resp.json()
        assert deleted_item["id"] == item_id
        assert deleted_item["deleted"] is True

        list_resp = await client.get("/items")
        items = list_resp.json()
        assert all(i["id"] != item_id for i in items)

        list_with_deleted = await client.get("/items", params={"show_deleted": True})
        items = list_with_deleted.json()
        deleted_item = next((i for i in items if i["id"] == item_id), None)
        assert deleted_item is not None
        assert deleted_item["deleted"] is True

    @pytest.mark.asyncio
    async def test_get_items_pagination(self, client: httpx.AsyncClient):
        for i in range(5):
            await client.post("/items", json={"name": f"Item{i}", "price": float(i + 10)})

        resp = await client.get("/items", params={"offset": 2, "limit": 2})
        items = resp.json()
        assert len(items) == 2
        assert items[0]["name"] == "Item2"
        assert items[1]["name"] == "Item3"

    @pytest.mark.asyncio
    async def test_get_items_show_deleted_with_price_filter(self, client: httpx.AsyncClient):
        item1 = (await client.post("/items", json={"name": "Active", "price": 50.0})).json()
        item2 = (await client.post("/items", json={"name": "DeletedCheap", "price": 10.0})).json()
        item3 = (await client.post("/items", json={"name": "DeletedExpensive", "price": 200.0})).json()

        await client.delete(f"/items/{item2['id']}")
        await client.delete(f"/items/{item3['id']}")

        resp = await client.get("/items", params={"show_deleted": True, "min_price": 100.0})
        items = resp.json()
        assert len(items) == 1
        assert items[0]["id"] == item3["id"]
        assert items[0]["deleted"] is True

    @pytest.mark.asyncio
    async def test_get_items_offset_without_limit(self, client: httpx.AsyncClient):
        for i in range(3):
            await client.post("/items", json={"name": f"Item{i}", "price": 10.0})

        resp = await client.get("/items", params={"offset": 1})
        items = resp.json()
        assert len(items) == 2
        assert items[0][("na"
                         "me")] == "Item1"

    @pytest.mark.asyncio
    async def test_get_items_show_deleted_with_price_filter(self, client: httpx.AsyncClient):
        item1 = (await client.post("/items", json={"name": "Active", "price": 50.0})).json()
        item2 = (await client.post("/items", json={"name": "DeletedCheap", "price": 10.0})).json()
        item3 = (await client.post("/items", json={"name": "DeletedExpensive", "price": 200.0})).json()

        await client.delete(f"/items/{item2['id']}")
        await client.delete(f"/items/{item3['id']}")

        resp = await client.get("/items", params={"show_deleted": True, "min_price": 100.0})
        items = resp.json()
        assert len(items) == 1
        assert items[0]["id"] == item3["id"]
        assert items[0]["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_unknown_item(self, client: httpx.AsyncClient):

        id = uuid4()
        resp = await client.delete(f"/items/{id}")
        assert resp.json()["msg"] == "Ничего не найдено"