from typing import Dict, Optional
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect


class ChatRoomManager:
    def __init__(self) -> None:
        self.rooms: Dict[str, set[WebSocket]] = {}
        self.usernames: Dict[WebSocket, str] = {}

    async def connect(self, room: str, websocket: WebSocket) -> str:
        await websocket.accept()
        username = f"user-{uuid4().hex[:8]}"
        self.rooms.setdefault(room, set()).add(websocket)
        self.usernames[websocket] = username
        return username

    def disconnect(self, room: str, websocket: WebSocket) -> None:
        connections = self.rooms.get(room)
        if connections is not None and websocket in connections:
            connections.remove(websocket)
            if not connections:
                self.rooms.pop(room, None)
        self.usernames.pop(websocket, None)

    async def broadcast(self, room: str, message: str, sender: Optional[WebSocket] = None) -> None:
        for ws in list(self.rooms.get(room, set())):
            if sender is not None and ws is sender:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(room, ws)

    def username_for(self, websocket: WebSocket) -> str:
        return self.usernames.get(websocket, "unknown")


chat_manager = ChatRoomManager()


async def handle_chat(websocket: WebSocket, chat_name: str) -> None:
    username = await chat_manager.connect(chat_name, websocket)
    try:
        while True:
            message = await websocket.receive_text()
            formatted = f"{username} :: {message}"
            await chat_manager.broadcast(chat_name, formatted, sender=websocket)
    except WebSocketDisconnect:
        chat_manager.disconnect(chat_name, websocket)


def register_chat_routes(app) -> None:
    @app.websocket("/chat/{chat_name}")
    async def chat_websocket(websocket: WebSocket, chat_name: str):
        await handle_chat(websocket, chat_name)


