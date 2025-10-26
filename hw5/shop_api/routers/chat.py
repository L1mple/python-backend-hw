from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from collections import defaultdict
import random
import string
from typing import Dict, List

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
    try:
        while True:
            data = await websocket.receive_text()
            message = f"{username} :: {data}"
            for ws in chat_rooms[chat_name]:
                if ws != websocket:
                    await ws.send_text(message)
    except WebSocketDisconnect:
        chat_rooms[chat_name].remove(websocket)
        del usernames[websocket]
