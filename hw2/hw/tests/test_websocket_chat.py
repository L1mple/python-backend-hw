from __future__ import annotations


def test_websocket_chat_basic(client):
    with client.websocket_connect("/chat/room42") as ws1:
        with client.websocket_connect("/chat/room42") as ws2:
            # второй получит joined-сообщение о первом
            # (сообщение может прийти и в другой момент, поэтому отправим ping)
            ws1.send_text("hello")
            msg = ws2.receive_text()
            # Либо это "* user-xxxx joined *", либо само сообщение ws1
            assert ("joined" in msg) or (":: hello" in msg)

            # теперь гарантированно получаем сообщение
            ws1.send_text("ping")
            got = ws2.receive_text()
            assert ":: ping" in got
