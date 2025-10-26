from http import HTTPStatus
import importlib

import pytest
from fastapi.testclient import TestClient

from shop_api.main import app, chat_manager, chat_websocket, WebSocketDisconnect
from shop_api import db as db_mod
from shop_api.models import Cart as CartModel, CartItem as CartItemModel


client = TestClient(app)


def test_get_item_not_found() -> None:
    response = client.get("/item/999999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_put_item_not_found() -> None:
    response = client.put("/item/999999999", json={"name": "x", "price": 1.0})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_put_item_deleted_returns_404(existing_item: dict) -> None:
    item_id = existing_item["id"]
    client.delete(f"/item/{item_id}")
    response = client.put(f"/item/{item_id}", json={"name": "new", "price": 2.5})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_patch_item_not_found() -> None:
    response = client.patch("/item/999999999", json={"name": "x"})
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_delete_item_nonexistent_ok() -> None:
    response = client.delete("/item/987654321")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"status": "ok"}


def test_get_cart_not_found() -> None:
    response = client.get("/cart/999999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_item_to_cart_missing_cart(existing_item: dict) -> None:
    item_id = existing_item["id"]
    response = client.post(f"/cart/999999999/add/{item_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_item_to_cart_missing_item(existing_empty_cart_id: int) -> None:
    response = client.post(f"/cart/{existing_empty_cart_id}/add/999999999")
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_cart_with_orphan_item_skips_and_zero_price() -> None:
    with db_mod.session_scope() as s:
        cart = CartModel()
        s.add(cart)
        s.commit()
        s.refresh(cart)
        s.add(CartItemModel(cart_id=cart.id, item_id=999999999, quantity=3))
        s.commit()

        cart_id = cart.id

    resp = client.get(f"/cart/{cart_id}")
    assert resp.status_code == HTTPStatus.OK
    data = resp.json()
    assert data["items"] == []
    assert data["price"] == 0.0


def test_build_database_url_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    url = db_mod._build_database_url()
    assert url.startswith("sqlite")


class RecordingWS:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def accept(self):
        return None

    async def send_text(self, message: str):
        self.sent.append(message)


@pytest.mark.asyncio
async def test_chat_manager_connect_broadcast_disconnect() -> None:
    room = "room-a"
    ws1 = RecordingWS()
    ws2 = RecordingWS()

    name1 = await chat_manager.connect(room, ws1)
    name2 = await chat_manager.connect(room, ws2)
    assert name1.startswith("user-") and name2.startswith("user-")

    await chat_manager.broadcast(room, "hello", sender=ws1)
    assert ws1.sent == []
    assert ws2.sent == ["hello"]

    chat_manager.disconnect(room, ws1)
    chat_manager.disconnect(room, ws2)
    assert room not in chat_manager.rooms


class LoopWS:
    def __init__(self, messages: list[str]) -> None:
        self._messages = list(messages)
        self.sent: list[str] = []

    async def accept(self):
        return None

    async def receive_text(self) -> str:
        if self._messages:
            return self._messages.pop(0)
        raise WebSocketDisconnect()

    async def send_text(self, message: str):
        self.sent.append(message)


@pytest.mark.asyncio
async def test_chat_websocket_loop_and_disconnect() -> None:
    room = "room-b"
    ws = LoopWS(["hi"])
    await chat_websocket(ws, room)
    assert room not in chat_manager.rooms or ws not in chat_manager.rooms.get(room, set())
    