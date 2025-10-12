from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from collections import defaultdict
import random
import string
from typing import Dict, List
from prometheus_client import Counter, Gauge

ws_connections = Gauge("shop_ws_connections", "Active WebSocket connections", ["chat_name"])
ws_messages_total = Counter("shop_ws_messages_total", "Total WebSocket messages sent", ["chat_name"])

router = APIRouter(prefix="/chat", tags=["chat"])

chat_rooms: Dict[str, List[WebSocket]] = defaultdict(list)
usernames: Dict[WebSocket, str] = {}

def random_username() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

@router.websocket("/{chat_name}")
async def websocket_chat(websocket: WebSocket, chat_name: str):
    await websocket.accept()
    username = random_username()
    usernames[websocket] = username
    chat_rooms[chat_name].append(websocket)
    ws_connections.labels(chat_name=chat_name).inc()  # <--- увеличиваем число соединений

    try:
        while True:
            data = await websocket.receive_text()
            message = f"{username} :: {data}"
            for ws in chat_rooms[chat_name]:
                if ws != websocket:
                    await ws.send_text(message)
                    ws_messages_total.labels(chat_name=chat_name).inc()  # <--- увеличиваем счетчик сообщений
    except WebSocketDisconnect:
        chat_rooms[chat_name].remove(websocket)
        del usernames[websocket]
        ws_connections.labels(chat_name=chat_name).dec()  # <--- уменьшаем число соединений

