import sys

from websocket import create_connection

if len(sys.argv) < 2:
    print("Usage: python client.py <chat_name>")
    sys.exit(1)

chat_name = sys.argv[1]
ws = create_connection(f"ws://localhost:8000/chat/{chat_name}")

print(f"Connected to chat room: {chat_name}")

while True:
    message = input("Enter message: ")
    ws.send(message)
    response = ws.recv()
    print(response)  # Получаем broadcast
