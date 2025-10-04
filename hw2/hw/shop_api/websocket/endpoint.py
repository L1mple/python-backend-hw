from fastapi import WebSocket, WebSocketDisconnect

from .connection_manager import ConnectionManager


# Глобальный менеджер соединений
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, chat_name: str):
    """WebSocket endpoint для чата"""
    await manager.connect(websocket, chat_name)
    
    try:
        while True:
            # Получаем сообщение от клиента
            data = await websocket.receive_text()
            
            # Получаем имя пользователя
            username = manager.user_names.get(websocket, "Unknown")
            
            # Формируем сообщение в формате "username :: message"
            formatted_message = f"{username} :: {data}"
            
            # Отправляем всем в комнате
            await manager.broadcast_to_room(chat_name, formatted_message)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_name)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, chat_name)
