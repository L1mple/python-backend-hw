from fastapi.testclient import TestClient
from shop_api.main import app
import threading

client = TestClient(app)


def test_chat_broadcast():
    with (
        client.websocket_connect("/chat/testroom") as ws1,
        client.websocket_connect("/chat/testroom") as ws2
    ):
        ws1.send_text("Hello world!")
        message = ws2.receive_text()

        assert "Hello world!" in message
        assert "::" in message


def test_chat_isolation_between_rooms():
    with (
        client.websocket_connect("/chat/testroom") as ws1,
        client.websocket_connect("/chat/anotherroom") as ws2
    ):
        ws1.send_text("Message to room1")

        received = []

        def try_receive():
            try:
                msg = ws2.receive_text()
                received.append(msg)
            except Exception:
                pass

        t = threading.Thread(target=try_receive, daemon=True)
        t.start()
        t.join(timeout=0.5)

        assert not received
