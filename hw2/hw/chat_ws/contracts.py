from uuid import UUID

from pydantic import BaseModel

class ChatInfo(BaseModel):
    chat_name : str
    active_users : int = 0

class UserMessage(BaseModel):
    user_name : UUID
    chat_name : str
    message : str
