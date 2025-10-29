import asyncio
import sys

import websockets


async def chat_client(chat_name: str):
    uri = f"ws://localhost:8000/chat/{chat_name}"
    
    print(f"Подключение к чату '{chat_name}'...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Подключено к чату '{chat_name}'")
            print("Введите сообщение (или 'exit' для выхода):\n")
            
            async def receive_messages():
                try:
                    async for message in websocket:
                        print(f"\r{message}")
                        print("> ", end="", flush=True)
                except websockets.exceptions.ConnectionClosed:
                    print("\n[Соединение закрыто]")
            
            async def send_messages():
                try:
                    while True:
                        message = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: input("> ")
                        )
                        
                        if message.lower() == "exit":
                            break
                        
                        if message.strip():
                            await websocket.send(message)
                except (KeyboardInterrupt, EOFError):
                    pass
            
            await asyncio.gather(
                receive_messages(),
                send_messages(),
            )
            
    except Exception as e:
        print(f"Ошибка: {e}")
        print("\nУбедитесь, что сервер запущен:")
        print("  cd hw2/hw && uvicorn shop_api.main:app --reload")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python test_chat_client.py <chat_name>")
        print("Пример: python test_chat_client.py general")
        sys.exit(1)
    
    chat_name = sys.argv[1]
    
    try:
        asyncio.run(chat_client(chat_name))
    except KeyboardInterrupt:
        print("\n[Выход]")

