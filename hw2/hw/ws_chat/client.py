import asyncio
import sys
import websockets
from websockets import ConnectionClosedOK, ConnectionClosedError

async def chat_client(chat_name: str):
    uri = f"ws://localhost:8000/chat/{chat_name}"
    try:
        async with websockets.connect(uri) as ws:
            print(f"Connected to chat '{chat_name}'. Enter messages (Ctrl+C to exit).")
            loop = asyncio.get_running_loop()

            async def receiver():
                try:
                    async for msg in ws:
                        print(msg)
                except (ConnectionClosedOK, ConnectionClosedError):
                    print("The connection was closed by the server.")
                except Exception as e:
                    print("Error receiving:", e)

            async def sender():
                try:
                    while True:
                     
                        text = await loop.run_in_executor(None, input, "> ")
                        if text is None:
                            continue
                        text = text.strip()
                        if text == "":
                            continue
                        await ws.send(text)
                       
                        print(f"(you) :: {text}")
                except (EOFError, KeyboardInterrupt):
                    
                    try:
                        await ws.close()
                    except Exception:
                        pass

            await asyncio.gather(receiver(), sender())

    except ConnectionRefusedError:
        print("Failed to connect: Please check if the server (uvicorn) is running.")
    except Exception as e:
        print("Connection/client operation error:", e)

if __name__ == "__main__":
    chat = sys.argv[1] if len(sys.argv) > 1 else "testroom"
    try:
        asyncio.run(chat_client(chat))
    except KeyboardInterrupt:
        print("\nThe client is completed. Goodbye!")
