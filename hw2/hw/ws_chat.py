from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import Dict
import random
import string

app = FastAPI(title="Chat API")


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Room: room1</h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'></ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/chat/room1");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages');
                var message = document.createElement('li');
                var content = document.createTextNode(event.data);
                message.appendChild(content);
                messages.appendChild(message);
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText");
                ws.send(input.value);
                input.value = '';
                event.preventDefault();
            }
        </script>
    </body>
</html>
"""

chat_rooms: Dict[str, Dict[WebSocket, str]] = {}

def generate_username() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/chat/{chat_name}")
async def websocket_chat(websocket: WebSocket, chat_name: str):
    await websocket.accept()
    username = generate_username()
    
    if chat_name not in chat_rooms:
        chat_rooms[chat_name] = {}
    chat_rooms[chat_name][websocket] = username
    
    try:
        while True:
            data = await websocket.receive_text()
            message = f"{username} :: {data}"
            for ws in chat_rooms[chat_name]:
                await ws.send_text(message)
    except WebSocketDisconnect:
        del chat_rooms[chat_name][websocket]
        if not chat_rooms[chat_name]:
            del chat_rooms[chat_name]
