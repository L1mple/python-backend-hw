from websocket import create_connection

ws = create_connection("ws://localhost:8000/chat/chat2")

while True:
    print(ws.recv())
    message = input("Enter message: ")
    ws.send(message)