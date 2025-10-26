from fastapi import FastAPI
from shop_api.routers import items, carts
from shop_api.database import Base, engine

app = FastAPI(title="Shop API")

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(items.router)
app.include_router(carts.router)
