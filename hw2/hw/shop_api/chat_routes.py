from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .chat_manager import chat_manager

router = APIRouter(tags=["chat"])


@router.websocket("/chat/{chat_name}")
async def websocket_chat(websocket: WebSocket, chat_name: str):
    room = chat_manager.get_or_create_room(chat_name)
    username = await room.add_user(websocket)
    
    await room.broadcast(f"joined the chat", username)
    
    try:
        while True:
            message = await websocket.receive_text()
            
            await room.broadcast(message, username)
            
    except WebSocketDisconnect:
        room.remove_user(username)
        await room.broadcast(f"left the chat", username)
        
        chat_manager.cleanup_empty_rooms()

