from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from shop_api.chat_manager import chat_manager



router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.websocket("/{chat_name}")
async def websocket_endpoint(websocket: WebSocket, chat_name: str):
    try:
        await chat_manager.connect(websocket, chat_name)
        while True:
            data = await websocket.receive_text()
            await chat_manager.publish(websocket, data)
    except WebSocketDisconnect:
        pass
    finally:
        await chat_manager.disconnect(websocket)