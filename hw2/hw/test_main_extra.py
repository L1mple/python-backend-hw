import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

from shop_api import main

client = TestClient(main.app)


def test_metrics_middleware_counts_requests() -> None:
    r1 = client.get("/item")
    assert r1.status_code == 200

    r2 = client.get("/metrics")
    assert r2.status_code == 200
    text = r2.text

    assert "http_requests_total" in text
    assert 'endpoint="/item"' in text


def test_cart_helpers_and_flow() -> None:
    item = client.post("/item", json={"name": "foo", "price": 1.5}).json()
    cart = client.post("/cart").json()

    client.post(f"/cart/{cart['id']}/add/{item['id']}")

    db = main.SessionLocal()
    try:
        items = main._cart_items(db, cart["id"])
        price = main._cart_price(db, cart["id"])

        assert isinstance(items, list)
        assert items[0].id == item["id"]
        assert items[0].quantity >= 1
        assert price == pytest.approx(1.5, rel=1e-6)
    finally:
        db.close()


class DummyWS:
    def __init__(self):
        self.sent: list[str] = []

    async def accept(self):
        return None

    async def send_text(self, text: str):
        self.sent.append(text)


@pytest.mark.asyncio
async def test_connection_manager_broadcast_and_disconnect_behavior() -> None:
    cm = main.ConnectionManager()

    ws1 = DummyWS()
    ws2 = DummyWS()

    user1 = await cm.connect("room_x", ws1)
    user2 = await cm.connect("room_x", ws2)

    # broadcast from ws1 -> ws2 should receive a message with user1 as sender
    await cm.broadcast("room_x", ws1, "hello")
    assert len(ws2.sent) == 1
    assert ws2.sent[0] == f"{user1} :: hello"

    cm.disconnect("room_x", ws1)
    assert "room_x" not in cm.active_connections


def test_websocket_endpoint_roundtrip():
    with client.websocket_connect("/chat/room_test") as ws1, client.websocket_connect(
        "/chat/room_test"
    ) as ws2:
        ws1.send_text("hey")
        # ws2 should receive a message
        data = ws2.receive_text()
        assert ":: hey" in data
