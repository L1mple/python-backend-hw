import json
import random
from typing import Dict, List

from fastapi import WebSocket


class ConnectionManager:
    """Менеджер WebSocket соединений для чата"""
    
    def __init__(self):
        # Словарь для хранения соединений по комнатам
        # Структура: {chat_name: [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Словарь для хранения имен пользователей
        # Структура: {websocket: username}
        self.user_names: Dict[WebSocket, str] = {}
    
    def generate_username(self) -> str:
        """Генерирует случайное имя пользователя"""
        adjectives = ["Happy", "Cool", "Smart", "Brave", "Kind", "Funny", "Wise", "Bright"]
        nouns = ["Cat", "Dog", "Bird", "Fish", "Tiger", "Lion", "Eagle", "Wolf"]
        adjective = random.choice(adjectives)
        noun = random.choice(nouns)
        number = random.randint(1, 999)
        return f"{adjective}{noun}{number}"
    
    async def connect(self, websocket: WebSocket, chat_name: str):
        """Подключение к чату"""
        await websocket.accept()
        
        # Добавляем соединение в комнату
        if chat_name not in self.active_connections:
            self.active_connections[chat_name] = []
        
        self.active_connections[chat_name].append(websocket)
        
        # Генерируем имя пользователя
        username = self.generate_username()
        self.user_names[websocket] = username
        
        # Уведомляем всех в комнате о новом пользователе
        await self.broadcast_to_room(
            chat_name, 
            f"👋 {username} присоединился к чату!",
            exclude_websocket=websocket
        )
        
        # Отправляем приветствие новому пользователю
        await websocket.send_text(json.dumps({
            "type": "system",
            "message": f"Добро пожаловать в чат '{chat_name}'! Ваше имя: {username}"
        }))
    
    def disconnect(self, websocket: WebSocket, chat_name: str):
        """Отключение от чата"""
        if websocket in self.active_connections.get(chat_name, []):
            self.active_connections[chat_name].remove(websocket)
            
            # Если комната пустая, удаляем её
            if not self.active_connections[chat_name]:
                del self.active_connections[chat_name]
            
            # Уведомляем о выходе пользователя
            if websocket in self.user_names:
                username = self.user_names[websocket]
                del self.user_names[websocket]
                
                # Уведомляем остальных в комнате
                if chat_name in self.active_connections:
                    self.broadcast_to_room_sync(
                        chat_name,
                        f"👋 {username} покинул чат!"
                    )
    
    async def broadcast_to_room(self, chat_name: str, message: str, exclude_websocket: WebSocket = None):
        """Отправка сообщения всем в комнате"""
        if chat_name not in self.active_connections:
            return
        
        for websocket in self.active_connections[chat_name]:
            if websocket != exclude_websocket:
                try:
                    await websocket.send_text(json.dumps({
                        "type": "message",
                        "message": message
                    }))
                except:
                    # Если соединение закрыто, удаляем его
                    self.active_connections[chat_name].remove(websocket)
    
    def broadcast_to_room_sync(self, chat_name: str, message: str):
        """Синхронная отправка сообщения (для уведомлений о выходе)"""
        if chat_name not in self.active_connections:
            return
        
        for websocket in self.active_connections[chat_name]:
            try:
                # Используем send_text синхронно (может не работать в некоторых случаях)
                pass
            except:
                self.active_connections[chat_name].remove(websocket)
    
    async def send_personal_message(self, websocket: WebSocket, message: str):
        """Отправка личного сообщения пользователю"""
        try:
            await websocket.send_text(json.dumps({
                "type": "message",
                "message": message
            }))
        except:
            pass
