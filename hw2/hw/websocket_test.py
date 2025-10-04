from fastapi.testclient import TestClient
from shop_api.main import app

client = TestClient(app)


def test_chat_broadcast():
    with client.websocket_connect("/chat/testroom") as ws1, client.websocket_connect("/chat/testroom") as ws2:
        ws1.send_text("Hello world!")
        message = ws2.receive_text()

        assert "Hello world!" in message
        assert "::" in message 