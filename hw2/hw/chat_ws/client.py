import asyncio
import requests
import httpx
from typing import List

import websockets
from aioconsole import ainput

from contracts import UserMessage, ChatInfo

def get_chats() -> List[str]:
    chats : List[dict] = requests.get('http://localhost:8000/chats').json()
    chat_names = []
    for chat in chats:
        print(f"{chat['chat_name']} : {chat['active_users']} online")
        chat_names.append(chat['chat_name'])
    return chat_names

async def send_loop(username : str, chat_name : str):
    async with httpx.AsyncClient() as client:
        while True:
            message = await ainput()
            data = {"user_name" : username, "chat_name" : chat_name, "message" : message}
            await client.post('http://localhost:8000/publish', json=data)

async def recive_loop(ws):
    async for incoming in ws:
        print(incoming)

async def chat(chat_name : str):
    async with websockets.connect(f"ws://localhost:8000/subscribe/{chat_name}") as ws:
        username = await ws.recv()
        await asyncio.gather(recive_loop(ws), send_loop(username, chat_name))

if __name__ == "__main__":
    chats = get_chats()
    print(chats)
    picked_chat = input()
    asyncio.run(chat(picked_chat))
