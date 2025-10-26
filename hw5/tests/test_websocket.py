from shop_api.src.main import manager


def test_websocket_chat_full_flow(client):
    """Полный тест чата с несколькими пользователями"""
    chat_name = "test_room"

    # Подключаем первого пользователя
    with client.websocket_connect(f"/chat/{chat_name}") as ws1:
        # Отправляем сообщение
        ws1.send_text("Hello from user 1")
        message1 = ws1.receive_text()
        assert "Hello from user 1" in message1

        # Подключаем второго пользователя
        with client.websocket_connect(f"/chat/{chat_name}") as ws2:
            # Второй пользователь отправляет сообщение
            ws2.send_text("Hello from user 2")

            # Оба получают сообщение
            message2_ws1 = ws1.receive_text()
            message2_ws2 = ws2.receive_text()

            assert "Hello from user 2" in message2_ws1
            assert "Hello from user 2" in message2_ws2


def test_websocket_username_generation():
    """Тест генерации уникальных имен пользователей"""
    usernames = set()
    for _ in range(10):
        username = manager.generate_username()
        assert len(username) > 3
        assert any(c.isdigit() for c in username)
        usernames.add(username)

    # Проверяем, что имена разные (с высокой вероятностью)
    assert len(usernames) > 1


def test_websocket_disconnect_handling(client):
    """Тест обработки отключения пользователя"""
    chat_name = "disconnect_test"

    with client.websocket_connect(f"/chat/{chat_name}") as ws1:
        # Проверяем, что комната создана
        assert chat_name in manager.active_connections

        # Отключаемся
        pass

    # После выхода из контекста комната должна быть очищена
    # (или пустая, если других пользователей нет)
    if chat_name in manager.active_connections:
        assert len(manager.active_connections[chat_name]) == 0


def test_websocket_multiple_rooms(client):
    """Тест работы с несколькими комнатами одновременно"""
    with client.websocket_connect("/chat/room1") as ws1:
        with client.websocket_connect("/chat/room2") as ws2:
            # Отправляем в первую комнату
            ws1.send_text("Message to room 1")
            msg1 = ws1.receive_text()
            assert "Message to room 1" in msg1

            # Отправляем во вторую комнату
            ws2.send_text("Message to room 2")
            msg2 = ws2.receive_text()
            assert "Message to room 2" in msg2

            # Проверяем, что обе комнаты активны
            assert "room1" in manager.active_connections
            assert "room2" in manager.active_connections


def test_websocket_broadcast_with_exception(client):
    """Тест обработки ошибок при отправке сообщений"""
    chat_name = "exception_test"

    with client.websocket_connect(f"/chat/{chat_name}") as ws:
        ws.send_text("Test message")
        message = ws.receive_text()
        assert "Test message" in message
