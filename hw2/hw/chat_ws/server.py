from dataclasses import dataclass, field
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from contracts import UserMessage, ChatInfo

app = FastAPI()

@dataclass(slots=True)
class Broadcaster:
    chat_subscribers : Dict[str, List[WebSocket]] = field(init=False, default_factory=dict)

    async def subscribe(self, chat_name : str, ws : WebSocket):
        await ws.accept()
        self.chat_subscribers[chat_name] = self.chat_subscribers.get(chat_name, []) + [ws]

    def unsubscribe(self, chat_name : str, ws : WebSocket):
        self.chat_subscribers[chat_name].remove(ws)

    def get_chats(self):
        return [ChatInfo(chat_name=name, active_users=len(users)) for name, users in self.chat_subscribers.items()]

    async def publish(self, chat_name : str, message : str):
        for ws in self.chat_subscribers[chat_name]:
            await ws.send_text(message)

broadcaster = Broadcaster()

@app.get("/chats", response_model=List[ChatInfo])
def get_chats():
    return broadcaster.get_chats()


@app.post("/publish")
async def publish(user_message : UserMessage):
    user_name = user_message.user_name
    chat_name = user_message.chat_name
    message = user_message.message

    await broadcaster.publish(
        chat_name,
        f"{user_name} : {message}"
    )

@app.websocket("/subscribe/{chat_name}")
async def subscribe(websocket : WebSocket, chat_name : str):
    client_id = uuid4()
    await broadcaster.subscribe(chat_name, websocket)
    await websocket.send_text(str(client_id))
    await broadcaster.publish(
        chat_name,
        f"client {client_id} subscribed"
    )

    try:
        while True:
            text = await websocket.receive_text()
            await broadcaster.publish(chat_name, text)
    except WebSocketDisconnect:
        broadcaster.unsubscribe(chat_name, websocket)
        await broadcaster.publish(chat_name, f"client {client_id} unsubscribed")
