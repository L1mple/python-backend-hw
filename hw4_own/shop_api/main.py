from __future__ import annotations

from fastapi import FastAPI

from shop_api.core.db import Base, engine
from shop_api.routers.item import router as item
from shop_api.routers.cart import router as cart
from shop_api.routers.chat import router as chat

app = FastAPI(title="Shop API (SQLAlchemy + SQLite)")

@app.on_event("startup")
async def on_startup() -> None:
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(item)
app.include_router(cart)
app.include_router(chat)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8001)
