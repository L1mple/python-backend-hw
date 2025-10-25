import sys
import threading
import time

from websocket import create_connection

# Проверяем, что пользователь указал имя комнаты
if len(sys.argv) < 2:
    print("Usage: python client.py <chat_name>")
    sys.exit(1)

chat_name = sys.argv[1]

# Подключаемся к серверу по WebSocket
ws = create_connection(f"ws://localhost:8000/chat/{chat_name}")
print(f"Connected to chat room: {chat_name}")


def receive_messages():
    """Слушаем сообщения от сервера в отдельном потоке"""
    while True:
        try:
            response = ws.recv()  # Получаю сообщение
            print(response)
        except Exception as e:
            print(f"Connection closed: {e}")
            break


# Запуск потока для получения сообщений
thread = threading.Thread(target=receive_messages)
thread.daemon = True  # Поток завершится, когда программа закончится
thread.start()

# цикл для ввода сообщений
while True:
    try:
        message = input("Enter message: ")
        if message.strip():  # Отправка только непустые сообщения
            ws.send(message)
        time.sleep(0.1)
    except KeyboardInterrupt:
        ws.close()  # закрытие соединение при Ctrl+C
        print("Disconnected from chat")
        break
    except Exception as e:
        print(f"Error: {e}")
        ws.close()
        break
