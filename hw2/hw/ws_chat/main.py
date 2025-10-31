from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import uuid

app = FastAPI()

chat_rooms: Dict[str, List[WebSocket]] = {}
usernames: Dict[WebSocket, str] = {}


@app.websocket("/chat/{chat_name}")
async def websocket_endpoint(websocket: WebSocket, chat_name: str):
    await websocket.accept()
    username = f"user_{uuid.uuid4().hex[:6]}"
    usernames[websocket] = username

    chat_rooms.setdefault(chat_name, []).append(websocket)
    await broadcast(chat_name, f"👋 {username} joined the chat!")

    try:
        while True:
            data = await websocket.receive_text()
            message = f"{username} :: {data}"
            await broadcast(chat_name, message, sender=websocket)
    except WebSocketDisconnect:
        chat_rooms[chat_name].remove(websocket)
        del usernames[websocket]
        await broadcast(chat_name, f"👋 {username} leaved the chat.")


async def broadcast(chat_name: str, message: str, sender: WebSocket = None):
    for conn in chat_rooms.get(chat_name, []):
        if conn != sender:
            try:
                await conn.send_text(message)
            except Exception:
                pass
