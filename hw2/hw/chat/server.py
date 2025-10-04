from dataclasses import dataclass, field
import random
import string


from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()


@dataclass(slots=True)
class ChatRoom:
    """Class representing a chat room."""

    subscribers: dict[WebSocket, str] = field(init=False, default_factory=dict)

    async def subscribe(self, ws: WebSocket) -> str:
        """Subscribes a new client to the chat room."""

        await ws.accept()
        random_letters = "".join(random.choices(string.ascii_lowercase, k=6))
        random_numbers = random.randint(10, 99)
        username = f"user_{random_letters+str(random_numbers)}"
        self.subscribers[ws] = username
        return username

    async def unsubscribe(self, ws: WebSocket) -> None:
        """Unsubscribes a client from the chat room."""

        if ws in self.subscribers:
            del self.subscribers[ws]

    async def broadcast(
        self, message: str, sender_ws: WebSocket, username: str | None = None
    ) -> None:
        """Broadcasts a message to all clients in the chat room."""

        if username is None:
            username = self.subscribers.get(sender_ws, "unknown")
        formatted_message = f"{username} :: {message}"

        for ws in self.subscribers:
            await ws.send_text(formatted_message)


# Dictionary to store chat rooms by their names
chat_rooms: dict[str, ChatRoom] = {}


def get_or_create_room(chat_name: str) -> ChatRoom:
    """Returns an existing chat room or creates a new one."""

    if chat_name not in chat_rooms:
        chat_rooms[chat_name] = ChatRoom()
    return chat_rooms[chat_name]


@app.websocket("/chat/{chat_name}")
async def ws_chat(ws: WebSocket, chat_name: str):
    """Handles WebSocket connections for the chat application."""

    room = get_or_create_room(chat_name)
    username = await room.subscribe(ws)

    try:
        while True:
            text = await ws.receive_text()
            await room.broadcast(text, ws)
    except WebSocketDisconnect:
        await room.unsubscribe(ws)

        # Send system message about user leaving
        for subscriber_ws in room.subscribers:
            await subscriber_ws.send_text(f"{username} left the chat")
