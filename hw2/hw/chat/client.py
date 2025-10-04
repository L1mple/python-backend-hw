from websocket import create_connection
import sys
import threading
import re

chat_name = sys.argv[1] if len(sys.argv) > 1 else "default"

if not re.fullmatch(r"[a-zA-Z0-9_-]+", chat_name):
    print("Error: Сhat name can only contain letters, digits, '-', and '_'")
    sys.exit(1)

ws = create_connection(f"ws://localhost:8000/chat/{chat_name}")

print(f"Connected to chat: {chat_name}")
print("Type message and press Enter to send. Ctrl+C to exit.\n")


def receive_messages():
    """Gets messages from the server and prints them to the console"""
    try:
        while True:
            message = ws.recv()
            print(f"\r{message}")
            print("> ", end="", flush=True)
    except KeyboardInterrupt:
        ws.close()


receiver_thread = threading.Thread(target=receive_messages, daemon=True)
receiver_thread.start()

try:
    while True:
        user_input = input("> ")
        if user_input:
            ws.send(user_input)
except KeyboardInterrupt:
    ws.close()
    print("\nDisconnected")
