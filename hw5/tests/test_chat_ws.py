import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient
from shop_api.routers import chat

app = FastAPI()
app.include_router(chat.router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_chat_rooms():
    chat.chat_rooms.clear()
    chat.usernames.clear()
    yield
    chat.chat_rooms.clear()
    chat.usernames.clear()


def test_random_username_length():
    username = chat.random_username()
    assert len(username) == 8
    assert username.isalnum()


def test_websocket_connect_and_disconnect():
    with client.websocket_connect("/chat/room1") as ws:
        ws.send_text("test")
    assert chat.chat_rooms.get("room1") == []
    assert len(chat.usernames) == 0


def test_websocket_send_receive_between_two_clients():
    with client.websocket_connect("/chat/roomX") as ws1, \
         client.websocket_connect("/chat/roomX") as ws2:

        ws1.send_text("Hello")
        msg = ws2.receive_text()
        assert " :: Hello" in msg

        ws2.send_text("Hi there")
        msg2 = ws1.receive_text()
        assert " :: Hi there" in msg2

    assert chat.chat_rooms.get("roomX") == []
    assert len(chat.usernames) == 0


def test_websocket_multiple_messages_and_disconnect():
    with client.websocket_connect("/chat/roomY") as ws1, \
         client.websocket_connect("/chat/roomY") as ws2:

        ws1.send_text("First")
        ws2.send_text("Second")

        msg2 = ws2.receive_text()
        assert " :: First" in msg2

        msg1 = ws1.receive_text()
        assert " :: Second" in msg1

    assert chat.chat_rooms.get("roomY") == []
    assert len(chat.usernames) == 0
