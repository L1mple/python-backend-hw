import random
from collections import defaultdict

from fastapi import WebSocket


class ChatRoom:
    def __init__(self):
        self.connections: dict[WebSocket, str] = {}
    
    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        username = self._generate_username()
        self.connections[ws] = username
        return username
    
    async def disconnect(self, ws: WebSocket) -> None:
        if ws in self.connections:
            del self.connections[ws]
    
    async def broadcast(self, message: str, sender_ws: WebSocket) -> None:
        username = self.connections.get(sender_ws, "Unknown")
        formatted_message = f"{username} :: {message}"
        
        for ws in self.connections:
            await ws.send_text(formatted_message)
    
    def _generate_username(self) -> str:
        adjectives = [
            "Happy", "Brave", "Calm", "Dreamy", "Eager",
            "Fancy", "Gentle", "Jolly", "Kind", "Lively",
            "Mighty", "Nice", "Proud", "Quick", "Smart",
            "Swift", "Wise", "Witty", "Young", "Zesty"
        ]
        
        nouns = [
            "Panda", "Tiger", "Eagle", "Dolphin", "Fox",
            "Wolf", "Bear", "Lion", "Owl", "Hawk",
            "Dragon", "Phoenix", "Unicorn", "Griffin", "Raven",
            "Falcon", "Panther", "Lynx", "Otter", "Shark"
        ]
        
        return f"{random.choice(adjectives)}{random.choice(nouns)}"


class ChatManager:
    def __init__(self):
        self.rooms: dict[str, ChatRoom] = defaultdict(ChatRoom)
    
    def get_room(self, chat_name: str) -> ChatRoom:
        return self.rooms[chat_name]


chat_manager = ChatManager()

