from pydantic import BaseModel, Field, ConfigDict


class ChatHello(BaseModel):
    type: str = Field("hello", frozen=True)
    room: str
    username: str


class ChatSystem(BaseModel):
    type: str = Field("system", frozen=True)
    text: str


class ChatMessage(BaseModel):
    type: str = Field("message", frozen=True)
    author: str
    text: str


class ClientInbound(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


model_config = ConfigDict(from_attributes=True)
