import pytest
from fastapi.testclient import TestClient
from shop_api.main import app


client = TestClient(app)


def test_websocket_connection():

    with client.websocket_connect("/chat/testroom") as websocket:

        data = websocket.receive_text()
        assert data.startswith("Вы подключены как: user-")

        websocket.send_text("Привет из теста!")

        response = websocket.receive_text()
        assert " :: Привет из теста!" in response
        assert response.startswith("user-")


def test_message_format_with_extracted_username():
    with client.websocket_connect("/chat/test") as ws:

        welcome = ws.receive_text()
        assert welcome.startswith("Вы подключены как: ")
        username = welcome.replace("Вы подключены как: ", "").strip()

        test_msg = "Привет, это тест!"
        ws.send_text(test_msg)

        response = ws.receive_text()

        expected = f"{username} :: {test_msg}"
        assert response == expected, f"Ожидалось '{expected}', получено '{response}'"