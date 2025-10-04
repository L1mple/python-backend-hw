from dataclasses import dataclass, field
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import random
import string

app = FastAPI(title="Chat API")


@dataclass(slots=True)
class ChatRoom:
    connections: list[WebSocket] = field(init=False, default_factory=list)
    usernames: dict[WebSocket, str] = field(init=False, default_factory=dict)

    async def add_connection(self, ws: WebSocket) -> str:
        await ws.accept()
        username = self.generate_username()
        self.connections.append(ws)
        self.usernames[ws] = username
        return username

    async def remove_connection(self, ws: WebSocket) -> None:
        if ws in self.connections:
            self.connections.remove(ws)
        if ws in self.usernames:
            del self.usernames[ws]

    async def broadcast_message(self, message: str, sender_ws: WebSocket) -> None:
        sender_username = self.usernames.get(sender_ws, "Unknown")
        formatted_message = f"{sender_username} :: {message}"
        
        for ws in self.connections:
            try:
                await ws.send_text(formatted_message)
            except:
                # Remove broken connections
                await self.remove_connection(ws)

    def generate_username(self) -> str:
        """Generate a random username for chat users"""
        return f"User_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"


# Store chat rooms by name
chat_rooms: dict[str, ChatRoom] = {}


@app.websocket("/chat/{chat_name}")
async def websocket_chat(ws: WebSocket, chat_name: str):
    # Get or create chat room
    if chat_name not in chat_rooms:
        chat_rooms[chat_name] = ChatRoom()
    
    room = chat_rooms[chat_name]
    
    # Add connection to room
    username = await room.add_connection(ws)
    
    # Notify others about new user
    await room.broadcast_message(f"{username} joined the chat", ws)
    
    try:
        while True:
            # Receive message from client
            message = await ws.receive_text()
            
            # Broadcast message to all users in the room
            await room.broadcast_message(message, ws)
            
    except WebSocketDisconnect:
        # Remove connection and notify others
        await room.remove_connection(ws)
        await room.broadcast_message(f"{username} left the chat", ws)
