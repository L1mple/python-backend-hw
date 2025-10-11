from fastapi import FastAPI
from .routes import items, carts
from .chat.websocket import chat_router

app = FastAPI(title="Shop API")

app.include_router(items.router, tags=["items"])
app.include_router(carts.router, tags=["carts"])
app.include_router(chat_router, tags=["chat"])

@app.get("/")
async def root():
    return {"message": "Shop API is running"}