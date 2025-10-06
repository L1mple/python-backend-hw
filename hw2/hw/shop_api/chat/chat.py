from faker import Faker
from fastapi import WebSocket, status
from typing import Dict, Set
from collections import defaultdict
import asyncio


def _random_name():
    return Faker().name()


class ChatManager:
    def __init__(self) -> None:
        self._rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._usernames: Dict[WebSocket, str] = {}
        self._rooms_lock = asyncio.Lock()
        self._room_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def connect(self, room: str, ws: WebSocket) -> str:
        await ws.accept()
        username = _random_name()
        async with self._rooms_lock:
            self._rooms[room].add(ws)
            self._usernames[ws] = username
        return username

    async def disconnect(self, room: str, ws: WebSocket) -> None:
        async with self._rooms_lock:
            if room in self._rooms:
                self._rooms[room].discard(ws)
                if not self._rooms[room]:
                    del self._rooms[room]
            self._usernames.pop(ws, None)

    async def broadcast(
        self, room: str, payload: dict, exclude: WebSocket | None = None
    ) -> None:
        async with self._rooms_lock:
            targets = list(self._rooms.get(room, ()))
        if not targets:
            return
        send_tasks = []
        for ws in targets:
            if exclude is not None and ws is exclude:
                continue
            send_tasks.append(self._safe_send(ws, payload, room))
        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)

    async def _safe_send(self, ws: WebSocket, payload: dict, room: str) -> None:
        try:
            await ws.send_json(payload)
        except Exception:
            try:
                await ws.close(code=status.WS_1011_INTERNAL_ERROR)
            finally:
                await self.disconnect(room, ws)
