from dataclasses import dataclass, field
from uuid import uuid4
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Chat API")

@dataclass(slots=True)
class Broadcaster:
    subscribers: dict[str, WebSocket] = field(init=False, default_factory=dict)

    async def subscribe(self, ws: WebSocket, username: str) -> None:
        await ws.accept()
        self.subscribers[username] = ws

    async def unsubscribe(self, username: str) -> None:
        self.subscribers.pop(username, None)

    async def publish(self, message: str, sender_username: Optional[str] = None) -> None:
        if sender_username is not None:
            formatted_message = f"{sender_username} :: {message}"
            for username, ws in self.subscribers.items():
                if username != sender_username:
                    await ws.send_text(formatted_message)
        else:
            for ws in self.subscribers.values():
                await ws.send_text(message)

chat_channels: dict[str, Broadcaster] = {}

@app.websocket("/chat/{chat_name}")
async def ws_chat(ws: WebSocket, chat_name: str):
    username = str(uuid4().hex[:8])
    if chat_name not in chat_channels:
        chat_channels[chat_name] = Broadcaster()
    broadcaster = chat_channels[chat_name]

    await broadcaster.subscribe(ws, username)
    await broadcaster.publish(f"user {username} joined the chat")

    try:
        while True:
            text = await ws.receive_text()
            await broadcaster.publish(text, username)
    except WebSocketDisconnect:
        await broadcaster.unsubscribe(username)
        await broadcaster.publish(f"left the chat", username)
        await broadcaster.publish(f"user {username} left the chat")
        if not broadcaster.subscribers:
            chat_channels.pop(chat_name, None)

    