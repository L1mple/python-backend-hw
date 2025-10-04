from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .api import carts, items
from .database import Base, engine
from .websocket import websocket_endpoint

app = FastAPI(title="Shop API")

# Create database tables
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(items.router)
app.include_router(carts.router)


@app.websocket("/chat/{chat_name}")
async def websocket_route(websocket: WebSocket, chat_name: str):
    """WebSocket endpoint для чата в комнате"""
    await websocket_endpoint(websocket, chat_name)


@app.get("/")
async def read_root():
    """Главная страница с чатом"""
    chat_file = os.path.join(os.path.dirname(__file__), "..", "chat_client.html")
    return FileResponse(chat_file)
