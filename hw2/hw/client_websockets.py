import asyncio
import websockets


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000


async def chat_client(room_name: str, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    uri = f"ws://{host}:{port}/chat/{room_name}"
    print(f"Подключение к комнате '{room_name}' по адресу {uri}...")

    try:
        async with websockets.connect(uri) as websocket:

            welcome = await websocket.recv()
            print(f"{welcome}\n")
            print("Чат запущен! Введите сообщение и нажмите Enter.")
            print("Чтобы выйти — введите 'quit' или нажмите Ctrl+C.\n")

            async def receive_messages():
                try:
                    while True:
                        message = await websocket.recv()
                        print(f"\r{message}")
                        print("Вы: ", end="", flush=True)
                except websockets.exceptions.ConnectionClosed:
                    print("\nСоединение закрыто сервером.")
                    return

            async def send_messages():
                loop = asyncio.get_event_loop()
                while True:

                    msg = await loop.run_in_executor(None, input, "Вы: ")
                    if msg.strip().lower() == 'quit':
                        break
                    if msg.strip():
                        await websocket.send(msg.strip())

            await asyncio.gather(receive_messages(), send_messages())

    except KeyboardInterrupt:
        print("\nВыход по запросу пользователя.")
    except Exception as e:
        print(f"\nОшибка подключения: {e}")
        print("Убедитесь, что сервер запущен: uvicorn main:app")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="WebSocket чат-клиент")
    parser.add_argument("room", help="Имя комнаты для подключения")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Хост сервера (по умолчанию: localhost)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Порт сервера (по умолчанию: 8000)")

    args = parser.parse_args()

    try:
        asyncio.run(chat_client(args.room, args.host, args.port))
    except KeyboardInterrupt:

        print("\nДо встречи!")


if __name__ == "__main__":
    main()