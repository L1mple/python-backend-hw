from __future__ import annotations
import asyncio
from typing import Final

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from shop_api.models.chat import ChatHello, ChatSystem, ChatMessage, ClientInbound
from shop_api.chat.chat import ChatManager

router = APIRouter(tags=["chat"])
manager: Final = ChatManager()

PING_INTERVAL = 20
IDLE_TIMEOUT = 60
MAX_MESSAGE_BYTES = 4096


@router.websocket("/chat/{room}")
async def chat_ws(ws: WebSocket, room: str):
    username = await manager.connect(room, ws)
    await ws.send_json(ChatHello(room=room, username=username).model_dump())
    await manager.broadcast(
        room, ChatSystem(text=f"{username} joined").model_dump(), exclude=ws
    )

    stop = asyncio.Event()
    idle_task = asyncio.create_task(_idle_watchdog(ws, stop))

    try:
        while True:
            raw = await ws.receive_text()
            if len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
                await ws.close(
                    code=status.WS_1009_MESSAGE_TOO_BIG, reason="message too large"
                )
                break

            data = ClientInbound.model_validate_json(raw)
            idle_task.cancel()
            idle_task = asyncio.create_task(_idle_watchdog(ws, stop))
            print(username)
            await manager.broadcast(
                room,
                ChatMessage(author=username, text=data.text).model_dump(),
                exclude=ws,
            )
    except WebSocketDisconnect:
        pass
    finally:
        stop.set()
        for task in (ping_task, idle_task):
            task.cancel()
        await manager.disconnect(room, ws)
        await manager.broadcast(room, ChatSystem(text=f"{username} left").model_dump())


async def _idle_watchdog(ws: WebSocket, stop: asyncio.Event) -> None:
    try:
        await asyncio.wait_for(stop.wait(), timeout=IDLE_TIMEOUT)
    except asyncio.TimeoutError:
        try:
            await ws.close(code=status.WS_1001_GOING_AWAY, reason="idle timeout")
        finally:
            stop.set()
