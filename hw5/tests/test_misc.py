import asyncio
from unittest.mock import AsyncMock

from shop_api.src.main import ConnectionManager


def test_websocket_chat():
    manager = ConnectionManager()

    mock_websocket = AsyncMock()
    mock_websocket.accept = AsyncMock()
    mock_websocket.receive_text = AsyncMock(return_value="Hello")
    mock_websocket.send_text = AsyncMock()

    username = asyncio.run(manager.connect(mock_websocket, "test_room"))
    assert username in [user for _, user in manager.active_connections["test_room"]]

    asyncio.run(manager.broadcast("Test message", "test_room", username))
    mock_websocket.send_text.assert_called_once()

    manager.disconnect(mock_websocket, "test_room")
    assert (
        "test_room" not in manager.active_connections
        or len(manager.active_connections["test_room"]) == 0
    )


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
