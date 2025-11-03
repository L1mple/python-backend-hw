from dataclasses import dataclass, field
from typing import Dict
from uuid import uuid4

from fastapi import WebSocket


@dataclass(slots=True)
class ChatRoom:
    name: str
    connections: Dict[str, WebSocket] = field(default_factory=dict)

    async def add_user(self, ws: WebSocket) -> str:
        await ws.accept()
        username = self._generate_random_username()
        self.connections[username] = ws
        return username

    def remove_user(self, username: str) -> None:
        if username in self.connections:
            del self.connections[username]

    async def broadcast(self, message: str, sender_username: str) -> None:
        formatted_message = f"{sender_username} :: {message}"

        disconnected_users = []
        for username, ws in self.connections.items():
            try:
                await ws.send_text(formatted_message)
            except Exception:
                disconnected_users.append(username)

        for username in disconnected_users:
            self.remove_user(username)

    def _generate_random_username(self) -> str:
        adj = [
            "Happy",
            "Brave",
            "Swift",
            "Clever",
            "Mighty",
            "Silent",
            "Golden",
            "Mystic",
            "Noble",
            "Wild",
        ]
        names = [
            "Tiger",
            "Eagle",
            "Dragon",
            "Phoenix",
            "Wolf",
            "Bear",
            "Fox",
            "Lion",
            "Hawk",
            "Panther",
        ]

        import random

        adjective = random.choice(adj)
        name = random.choice(names)
        unique_id = str(uuid4())[:4]

        return f"{adjective}{name}{unique_id}"


@dataclass(slots=True)
class ChatManager:
    rooms: Dict[str, ChatRoom] = field(default_factory=dict)

    def get_or_create_room(self, room_name: str) -> ChatRoom:
        if room_name not in self.rooms:
            self.rooms[room_name] = ChatRoom(name=room_name)
        return self.rooms[room_name]

    def cleanup_empty_rooms(self) -> None:
        empty_rooms = [
            name for name, room in self.rooms.items() if len(room.connections) == 0
        ]
        for room_name in empty_rooms:
            del self.rooms[room_name]


chat_manager = ChatManager()
