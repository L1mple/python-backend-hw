from websocket import create_connection

ws = create_connection("ws://localhost:8000/subscribe")

while True:
    print(ws.recv())
