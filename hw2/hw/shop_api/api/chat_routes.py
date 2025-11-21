from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from shop_api.websocket_chat import chat_manager

router = APIRouter()


@router.websocket("/chat/{chat_name}")
async def chat_endpoint(websocket: WebSocket, chat_name: str):
    room = chat_manager.get_room(chat_name)
    await room.connect(websocket)
    
    try:
        while True:
            message = await websocket.receive_text()
            await room.broadcast(message, websocket)
    except WebSocketDisconnect:
        await room.disconnect(websocket)

