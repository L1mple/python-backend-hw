import re
from fastapi.testclient import TestClient

from shop_api.main import app

USERNAME_RE = re.compile(r"^\[system\] :: your_name = (user-[0-9a-f]{4})$")


def _extract_username(system_msg: str) -> str:
    """
    Из приветственного сообщения вида:
      "[system] :: your_name = user-ab12"
    достаём "user-ab12".
    """
    m = USERNAME_RE.match(system_msg)
    assert m, f"unexpected system greeting format: {system_msg!r}"
    return m.group(1)


def test_websocket_broadcast_and_format():
    client = TestClient(app)

    # Подключаем двух пользователей к одной комнате и третьего — к другой
    with (
        client.websocket_connect("/chat/room1") as ws1,
        client.websocket_connect("/chat/room1") as ws2,
        client.websocket_connect("/chat/room2") as ws3,
    ):
        # Приветственные сообщения с именами
        u1 = _extract_username(ws1.receive_text())
        u2 = _extract_username(ws2.receive_text())
        u3 = _extract_username(ws3.receive_text())
        assert u1 != u2 and u1 != u3 and u2 != u3  # имена случайные и разные

        # user1 -> room1
        msg1 = "hello from 1"
        ws1.send_text(msg1)

        # Должно прийти ТОЛЬКО второму участнику той же комнаты
        got2 = ws2.receive_text()
        assert got2 == f"{u1} :: {msg1}"

        # user3 -> room2 (не должен мешать room1)
        ws3.send_text("ping from 3")

        # user2 -> room1
        msg2 = "hi from 2"
        ws2.send_text(msg2)

        # Должно прийти первому участнику room1
        got1 = ws1.receive_text()
        assert got1 == f"{u2} :: {msg2}"


def test_websocket_username_greeting_format():
    client = TestClient(app)
    with client.websocket_connect("/chat/any-room") as ws:
        greet = ws.receive_text()
        # Проверяем точный формат приветствия и шаблон username
        assert USERNAME_RE.match(greet), f"bad greeting: {greet!r}"
