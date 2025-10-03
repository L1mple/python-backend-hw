import asyncio
import websockets

async def chat_client(chat_name: str):
    uri = f"ws://localhost:8000/chat/{chat_name}"
    async with websockets.connect(uri) as websocket:
        print(f" Connected to the chat: {chat_name}")
        print("Welcome to the chat room!:")

        async def sender():
            while True:
                msg = input("> ")
                await websocket.send(msg)

        async def receiver():
            while True:
                msg = await websocket.recv()
                print(msg)

        await asyncio.gather(sender(), receiver())

if __name__ == "__main__":
    room = input("Chat-room name: ")
    asyncio.run(chat_client(room))
