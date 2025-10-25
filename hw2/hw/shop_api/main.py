from fastapi import FastAPI
from fastapi.responses import FileResponse
from prometheus_fastapi_instrumentator import Instrumentator
import os

from .api.cart import router as cart_router
from .api.item import router as item_router
from .ws import router as ws_router

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

app.include_router(cart_router)
app.include_router(item_router)
app.include_router(ws_router)

@app.get("/chat-client")
async def get_chat_client():
    chat_client_path = os.path.join(os.path.dirname(__file__), "ws", "chat.html")
    return FileResponse(chat_client_path)
