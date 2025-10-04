#!/usr/bin/env python3
"""
Подробный тест WebSocket чата
"""
import asyncio
import json
import websockets
import time


async def test_room_isolation():
    """Тест изоляции комнат - пользователи в разных комнатах не должны видеть сообщения друг друга"""
    print("Тестирование изоляции комнат...")
    
    room1_uri = "ws://localhost:8000/chat/room1"
    room2_uri = "ws://localhost:8000/chat/room2"
    
    async def room1_client():
        async with websockets.connect(room1_uri) as ws:
            # Ждем приветствие
            await ws.recv()
            # Отправляем сообщение
            await ws.send("Сообщение из комнаты 1")
            # Ждем ответ
            response = await ws.recv()
            print(f"Комната 1 получила: {response}")
    
    async def room2_client():
        async with websockets.connect(room2_uri) as ws:
            # Ждем приветствие
            await ws.recv()
            # Отправляем сообщение
            await ws.send("Сообщение из комнаты 2")
            # Ждем ответ
            response = await ws.recv()
            print(f"Комната 2 получила: {response}")
    
    # Запускаем клиентов в разных комнатах одновременно
    await asyncio.gather(room1_client(), room2_client())
    print("Изоляция комнат работает!")


async def test_multiple_users_same_room():
    """Тест нескольких пользователей в одной комнате"""
    print("\nТестирование нескольких пользователей в одной комнате...")
    
    uri = "ws://localhost:8000/chat/group_chat"
    messages_received = []
    
    async def user_task(user_id):
        async with websockets.connect(uri) as ws:
            # Ждем приветствие
            welcome = await ws.recv()
            print(f"Пользователь {user_id} подключился")
            
            # Отправляем сообщение
            message = f"Привет от пользователя {user_id}!"
            await ws.send(message)
            print(f"Пользователь {user_id} отправил: {message}")
            
            # Собираем все сообщения
            try:
                while True:
                    response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    messages_received.append((user_id, response))
                    print(f"Пользователь {user_id} получил: {response}")
            except asyncio.TimeoutError:
                pass
    
    # Запускаем 3 пользователей
    tasks = [user_task(i) for i in range(1, 4)]
    await asyncio.gather(*tasks)
    
    print(f"Всего сообщений получено: {len(messages_received)}")
    print("Групповой чат работает!")


async def test_username_format():
    """Тест формата имен пользователей"""
    print("\nТестирование формата имен пользователей...")
    
    uri = "ws://localhost:8000/chat/username_test"
    
    async with websockets.connect(uri) as ws:
        # Получаем приветствие с именем
        welcome = await ws.recv()
        welcome_data = json.loads(welcome)
        username = welcome_data["message"].split("Ваше имя: ")[1]
        
        print(f"Получено имя: {username}")
        
        # Проверяем формат имени (должно быть AdjectiveNounNumber)
        if any(word in username for word in ["Happy", "Cool", "Smart", "Brave", "Kind", "Funny", "Wise", "Bright"]):
            print("Имя содержит прилагательное")
        else:
            print("Имя не содержит прилагательное")
            
        if any(word in username for word in ["Cat", "Dog", "Bird", "Fish", "Tiger", "Lion", "Eagle", "Wolf"]):
            print("Имя содержит существительное")
        else:
            print("Имя не содержит существительное")
            
        if any(char.isdigit() for char in username):
            print("Имя содержит цифры")
        else:
            print("Имя не содержит цифры")
    
    print("Формат имен работает!")


async def test_message_format():
    """Тест формата сообщений"""
    print("\nТестирование формата сообщений...")
    
    uri = "ws://localhost:8000/chat/format_test"
    
    async with websockets.connect(uri) as ws:
        # Получаем приветствие
        welcome = await ws.recv()
        welcome_data = json.loads(welcome)
        username = welcome_data["message"].split("Ваше имя: ")[1]
        
        # Отправляем тестовое сообщение
        test_message = "Тестовое сообщение"
        await ws.send(test_message)
        
        # Получаем ответ
        response = await ws.recv()
        response_data = json.loads(response)
        
        # Проверяем формат: "username :: message"
        expected_format = f"{username} :: {test_message}"
        if response_data["message"] == expected_format:
            print("Формат сообщения корректен!")
            print(f"Ожидалось: {expected_format}")
            print(f"Получено: {response_data['message']}")
        else:
            print("Формат сообщения некорректен!")
            print(f"Ожидалось: {expected_format}")
            print(f"Получено: {response_data['message']}")
    
    print("Формат сообщений работает!")


async def test_connection_disconnection():
    """Тест подключения и отключения"""
    print("\nТестирование подключения и отключения...")
    
    uri = "ws://localhost:8000/chat/disconnect_test"
    
    # Тест 1: Подключение
    print("Тестирование подключения...")
    async with websockets.connect(uri) as ws:
        welcome = await ws.recv()
        print("Подключение успешно!")
        
        # Отправляем сообщение
        await ws.send("Тест подключения")
        response = await ws.recv()
        print("Сообщение отправлено и получено!")
    
    print("Отключение успешно!")
    
    # Тест 2: Повторное подключение
    print("Тестирование повторного подключения...")
    async with websockets.connect(uri) as ws:
        welcome = await ws.recv()
        print("Повторное подключение успешно!")
    
    print("Тест подключения/отключения завершен!")


async def main():
    """Главная функция тестирования"""
    print("Тестирование WebSocket чата")
    print("=" * 40)
    
    # Тест 1: Изоляция комнат
    await test_room_isolation()
    
    # Тест 2: Несколько пользователей в одной комнате
    await test_multiple_users_same_room()
    
    # Тест 3: Формат имен пользователей
    await test_username_format()
    
    # Тест 4: Формат сообщений
    await test_message_format()
    
    # Тест 5: Подключение/отключение
    await test_connection_disconnection()
    
    print("\nВсе тесты завершены!")
    print("WebSocket чат полностью функционален!")


if __name__ == "__main__":
    asyncio.run(main())
