from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

app = FastAPI()


@dataclass(slots=True)
class Broadcaster:
    subscribers: list[WebSocket] = field(init=False, default_factory=list)

    async def subscribe(self, ws: WebSocket) -> None:
        await ws.accept()
        self.subscribers.append(ws)

    async def unsubscribe(self, ws: WebSocket) -> None:
        self.subscribers.remove(ws)

    async def publish(self, message: str) -> None:
        for ws in self.subscribers:
            await ws.send_text(message)


broadcaster = Broadcaster()


@app.post("/publish")
async def post_publish(request: Request):
    message = (await request.body()).decode()
    await broadcaster.publish(message)


@app.websocket("/subscribe")
async def ws_subscribe(ws: WebSocket):
    client_id = uuid4()
    await broadcaster.subscribe(ws)
    await broadcaster.publish(f"client {client_id} subscribed")

    try:
        while True:
            text = await ws.receive_text()
            await broadcaster.publish(text)
    except WebSocketDisconnect:
        broadcaster.unsubscribe(ws)
        await broadcaster.publish(f"client {client_id} unsubscribed")
