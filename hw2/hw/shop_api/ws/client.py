from typing import Dict, Set
from fastapi import WebSocket

class ChatManager:
    def __init__(self):
        self.connections: Dict[str, Set[tuple[WebSocket, str]]] = {}
    
    async def connect(self, websocket: WebSocket, chat_name: str, username: str) -> str:
        await websocket.accept()
        self.connections.setdefault(chat_name, set()).add((websocket, username))
        await self._broadcast(chat_name, f"{username} подключился к чату", websocket)
        return username
    
    def disconnect(self, websocket: WebSocket, chat_name: str, username: str):
        self.connections.get(chat_name, set()).discard((websocket, username))
    
    async def send_message(self, chat_name: str, sender_websocket: WebSocket, sender_username: str, message: str):
        await self._broadcast(chat_name, f"{sender_username} :: {message}")
    
    async def send_disconnect_message(self, chat_name: str, username: str):
        await self._broadcast(chat_name, f"{username} покинул чат")
    
    async def _broadcast(self, chat_name: str, message: str, exclude: WebSocket = None):
        for ws, _ in list(self.connections.get(chat_name, set())):
            if ws != exclude:
                try:
                    await ws.send_text(message)
                except Exception:
                    self.connections.get(chat_name, set()).discard((ws, _))


chat_manager = ChatManager()
