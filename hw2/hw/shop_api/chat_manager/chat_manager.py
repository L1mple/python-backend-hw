import uuid
from typing import List, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect



class ChatManager:
    def __init__(self):

        self.rooms: Dict[str, List[WebSocket]] = {}
        self.user_data: Dict[WebSocket, tuple[str, str]] = {}

    def generate_username(self) -> str:
        return f"user-{uuid.uuid4().hex}"

    async def connect(self, websocket: WebSocket, chat_name: str) -> str:

        await websocket.accept()
        username = self.generate_username()

        if chat_name not in self.rooms:
            self.rooms[chat_name] = []

        self.rooms[chat_name].append(websocket)
        self.user_data[websocket] = (username, chat_name)

        await websocket.send_text(f"Вы подключены как: {username}")
        return username


    async def disconnect(self, websocket: WebSocket):

        if websocket not in self.user_data:
            return

        username, chat_name = self.user_data[websocket]
        del self.user_data[websocket]

        if chat_name in self.rooms:
            if websocket in self.rooms[chat_name]:
                self.rooms[chat_name].remove(websocket)
            # Удаляем пустую комнату
            if not self.rooms[chat_name]:
                del self.rooms[chat_name]


    async def publish(self, websocket: WebSocket, message: str):

        if websocket not in self.user_data:
            return

        username, chat_name = self.user_data[websocket]
        full_message = f"{username} :: {message}"

        if chat_name not in self.rooms:
            return

        disconnected = []
        for client in self.rooms[chat_name]:
            try:
                await client.send_text(full_message)
            except Exception:
                disconnected.append(client)

        for client in disconnected:
            if client in self.rooms[chat_name]:
                self.rooms[chat_name].remove(client)
                if client in self.user_data:
                    del self.user_data[client]



chat_manager = ChatManager()