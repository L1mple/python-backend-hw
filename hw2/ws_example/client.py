import websocket
import threading
import time

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Connection closed")

def on_open(ws):
    print("Connected to chat!")
    print("Type messages and press Enter to send them.")
    print("Type 'quit' to exit.")

def send_messages(ws):
    while True:
        message = input()
        if message.lower() == 'quit':
            ws.close()
            break
        ws.send(message)

if __name__ == "__main__":
    # Get chat room name from user
    chat_name = input("Enter chat room name: ").strip() or "general"
    
    # Create WebSocket connection
    ws = websocket.WebSocketApp(
        f"ws://localhost:8001/chat/{chat_name}",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    
    # Start message sending in a separate thread
    send_thread = threading.Thread(target=send_messages, args=(ws,))
    send_thread.daemon = True
    send_thread.start()
    
    # Run WebSocket
    ws.run_forever()
