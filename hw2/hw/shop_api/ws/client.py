from typing import Dict, Set
from fastapi import WebSocket
from prometheus_client import Gauge

# Метрики для мониторинга чата
chat_users_total = Gauge('chat_users_total', 'Total number of users in all chat rooms')
chat_users_by_room = Gauge('chat_users_by_room', 'Number of users by chat room', ['room'])
chat_messages_total = Gauge('chat_messages_sent_total', 'Total number of messages sent')

class ChatManager:
    def __init__(self):
        self.connections: Dict[str, Set[tuple[WebSocket, str]]] = {}
    
    async def connect(self, websocket: WebSocket, chat_name: str, username: str) -> str:
        await websocket.accept()
        self.connections.setdefault(chat_name, set()).add((websocket, username))
        
        self._update_metrics()
        
        await self._broadcast(chat_name, f"{username} подключился к чату")
        return username
    
    def disconnect(self, websocket: WebSocket, chat_name: str, username: str):
        self.connections.get(chat_name, set()).discard((websocket, username))
        
        self._update_metrics()
    
    async def send_message(self, chat_name: str, sender_websocket: WebSocket, sender_username: str, message: str):
        chat_messages_total.inc()  
        await self._broadcast(chat_name, f"{sender_username} :: {message}")
    
    async def send_disconnect_message(self, chat_name: str, username: str):
        await self._broadcast(chat_name, f"{username} покинул чат")
    
    def _update_metrics(self):
        total_users = sum(len(users) for users in self.connections.values())
        chat_users_total.set(total_users)
        
        for room_name, users in self.connections.items():
            chat_users_by_room.labels(room=room_name).set(len(users))
    
    async def _broadcast(self, chat_name: str, message: str, exclude: WebSocket = None):
        for ws, _ in list(self.connections.get(chat_name, set())):
            if ws != exclude:
                try:
                    await ws.send_text(message)
                except Exception:
                    self.connections.get(chat_name, set()).discard((ws, _))


chat_manager = ChatManager()
