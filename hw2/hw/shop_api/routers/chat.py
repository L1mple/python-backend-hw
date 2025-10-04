from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect, FastAPI
import secrets
import string

_rooms: Dict[str, Dict[str, WebSocket]] = {}


def _gen_username(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "user_" + "".join(secrets.choice(alphabet) for _ in range(length))


async def _broadcast(room: str, message: str, skip_ws: Optional[WebSocket] = None) -> None:
    conns = _rooms.get(room, {})
    for _, ws in list(conns.items()):
        if skip_ws is not None and ws is skip_ws:
            continue
        try:
            await ws.send_text(message)
        except Exception:
            pass


def register_chat(app: FastAPI) -> None:
    @app.websocket("/chat/{chat_name}")
    async def chat_websocket(websocket: WebSocket, chat_name: str):
        await websocket.accept()
        username = _gen_username()
        conns = _rooms.setdefault(chat_name, {})
        conns[username] = websocket
        try:
            while True:
                text = await websocket.receive_text()
                await _broadcast(chat_name, f"{username} :: {text}", skip_ws=websocket)
        except WebSocketDisconnect:
            pass
        finally:
            room = _rooms.get(chat_name)
            if room and username in room:
                room.pop(username, None)
                if not room:
                    _rooms.pop(chat_name, None)
