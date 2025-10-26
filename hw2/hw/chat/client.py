import asyncio
import websockets


async def receive_messages(websocket):
    try:
        async for message in websocket:
            print(message)
    except:
        pass


async def send_messages(websocket):
    loop = asyncio.get_running_loop()
    while True:
        try:
            message = await loop.run_in_executor(None, lambda: input())
            await websocket.send(message)
        except:
            break


async def main():
    chat_name = input("Chat name: ").strip()

    uri = f"ws://127.0.0.1:8000/chat/{chat_name}"
    async with websockets.connect(uri) as websocket:
        await asyncio.gather(
            receive_messages(websocket),
            send_messages(websocket)
        )


if __name__ == "__main__":
    asyncio.run(main())
