from __future__ import annotations

import asyncio
import secrets  # стандартная библиотека: https://docs.python.org/3/library/secrets.html
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["chat"])


class RoomManager:
    # Решил реализовать в одном файле систему чатов, чтобы проще было проверять
    def __init__(self) -> None:
        # room -> set of websockets
        self.rooms: dict[str, set[WebSocket]] = defaultdict(set)
        # websocket -> username
        self.usernames: dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _gen_username() -> str:
        # короткий случайный ник
        return f"user-{secrets.token_hex(2)}"

    async def connect(self, room: str, ws: WebSocket) -> str:
        await ws.accept()
        username = self._gen_username()
        async with self._lock:
            self.rooms[room].add(ws)
            self.usernames[ws] = username
        await ws.send_text(f"[system] :: your_name = {username}")
        return username

    async def disconnect(self, room: str, ws: WebSocket) -> None:
        async with self._lock:
            self.rooms[room].discard(ws)
            self.usernames.pop(ws, None)
            if not self.rooms[room]:
                self.rooms.pop(room, None)

    async def broadcast(
        self, room: str, text: str, sender: WebSocket | None = None
    ) -> None:
        async with self._lock:
            targets = list(self.rooms.get(room, ()))
        for ws in targets:
            if ws is sender:
                continue
            try:
                await ws.send_text(text)
            except Exception:
                try:
                    await self.disconnect(room, ws)
                except Exception:
                    pass


manager = RoomManager()


@router.websocket("/chat/{chat_name}")
async def chat_ws(websocket: WebSocket, chat_name: str):
    """
    Пользователи, подключённые к одному chat_name, получают сообщения друг друга.
    Формат сообщения: "{username} :: {message}".
    """
    username = await manager.connect(chat_name, websocket)
    try:
        while True:
            # Ждём текст от клиента
            msg = await websocket.receive_text()
            # Бродкастим другим пользователям в комнате (без эха отправителю)
            await manager.broadcast(chat_name, f"{username} :: {msg}", sender=websocket)
    except WebSocketDisconnect:
        await manager.disconnect(chat_name, websocket)
    except Exception:
        # Любая иная ошибка закрывает сокет и удаляет из комнаты
        await manager.disconnect(chat_name, websocket)
        try:
            await websocket.close()
        except Exception:
            pass
