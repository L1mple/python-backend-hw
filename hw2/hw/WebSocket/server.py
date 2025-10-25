from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import secrets
from typing import Dict, List

app = FastAPI(title="Chat Server")

rooms: Dict[str, List[WebSocket]] = {}
usernames: Dict[WebSocket, str] = {}

@app.websocket("/chat/{chat_name}")
async def chatroom(websocket: WebSocket, chat_name: str):
    await websocket.accept()
    username = f"user-{secrets.token_hex(3)}"
    usernames[websocket] = username

    if chat_name not in rooms:
        rooms[chat_name] = []
    rooms[chat_name].append(websocket)

    try:
        while True:
            msg = await websocket.receive_text()
            formatted = f"{username} :: {msg}"
            for client in rooms[chat_name]:
                if client != websocket:
                    await client.send_text(formatted)
    except WebSocketDisconnect:
        rooms[chat_name].remove(websocket)
        del usernames[websocket]
        if not rooms[chat_name]:
            del rooms[chat_name]
