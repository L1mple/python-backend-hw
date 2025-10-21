import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import asyncio


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.usernames: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, chat_name: str):
        await websocket.accept()

        if chat_name not in self.active_connections:
            self.active_connections[chat_name] = []

        self.active_connections[chat_name].append(websocket)

        username = f"User_{uuid.uuid4().hex[:8]}"
        self.usernames[websocket] = username

        await self.broadcast_message(
            chat_name,
            f"🟢 {username} :: присоединился к чату",
            exclude_websocket=websocket
        )

        await websocket.send_text(f"🤖 Добро пожаловать в чат '{chat_name}'! Ваше имя: {username}")

    def disconnect(self, websocket: WebSocket, chat_name: str):
        if chat_name in self.active_connections:
            if websocket in self.active_connections[chat_name]:
                self.active_connections[chat_name].remove(websocket)

            if not self.active_connections[chat_name]:
                del self.active_connections[chat_name]

        if websocket in self.usernames:
            username = self.usernames[websocket]
            del self.usernames[websocket]

            if chat_name in self.active_connections:
                self.broadcast_message_sync(
                    chat_name,
                    f"🔴 {username} :: покинул чат",
                    exclude_websocket=websocket
                )

    async def broadcast_message(self, chat_name: str, message: str, exclude_websocket: WebSocket = None):
        if chat_name in self.active_connections:
            for connection in self.active_connections[chat_name]:
                if connection != exclude_websocket:
                    try:
                        await connection.send_text(message)
                    except:
                        self.disconnect(connection, chat_name)

    def broadcast_message_sync(self, chat_name: str, message: str, exclude_websocket: WebSocket = None):
        """Синхронная версия для использования в disconnect"""
        if chat_name in self.active_connections:
            disconnected = []
            for connection in self.active_connections[chat_name]:
                if connection != exclude_websocket:
                    try:
                        asyncio.create_task(connection.send_text(message))
                    except:
                        disconnected.append(connection)

            for connection in disconnected:
                self.disconnect(connection, chat_name)

    async def handle_message(self, websocket: WebSocket, chat_name: str, message: str):
        username = self.usernames.get(websocket, "Unknown")
        formatted_message = f"{username} :: {message}"
        await self.broadcast_message(chat_name, formatted_message)


manager = ConnectionManager()
chat_router = APIRouter()


@chat_router.websocket("/chat/{chat_name}")
async def websocket_endpoint(websocket: WebSocket, chat_name: str):
    await manager.connect(websocket, chat_name)

    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_message(websocket, chat_name, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_name)