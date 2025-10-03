from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .client import chat_manager

router = APIRouter()


@router.websocket("/chat/{chat_name}")
async def websocket_endpoint(websocket: WebSocket, chat_name: str, username: str = Query(...)):
    username = await chat_manager.connect(websocket, chat_name, username)
    
    try:
        while True:
            message = await websocket.receive_text()
            await chat_manager.send_message(chat_name, websocket, username, message)
            
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket, chat_name, username)
        await chat_manager.send_disconnect_message(chat_name, username)
