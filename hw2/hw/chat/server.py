from collections import defaultdict
from typing import Dict, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uuid


app = FastAPI()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, chat_name: str) -> str:
        await websocket.accept()
        username = str(uuid.uuid4())
        self.active_connections[chat_name].append(websocket)
        return username

    def disconnect(self, websocket: WebSocket, chat_name: str):
        self.active_connections[chat_name].remove(websocket)
        if chat_name in self.active_connections and len(self.active_connections[chat_name]) == 0:
            del self.active_connections[chat_name]

    async def broadcast(self, message: str, chat_name: str, websocket = None):
        for connection in self.active_connections[chat_name]:
            if connection != websocket:
                await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/chat/{chat_name}")
async def websocket_endpoint(websocket: WebSocket, chat_name: str):
    username = await manager.connect(websocket, chat_name)

    await manager.broadcast(f"--- {username} joined the chat ---", chat_name)

    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"{username} :: {data}", chat_name, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_name)
        await manager.broadcast(f"--- {username} left the chat ---", chat_name)