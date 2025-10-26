from fastapi import FastAPI
from shop_api.db.session import engine, Base

from shop_api.handlers.cart import router as cart_router
from shop_api.handlers.item import router as item_router
from shop_api.models.cart import Cart
from shop_api.models.item import Item


app = FastAPI(title="Shop API")

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(cart_router)
app.include_router(item_router)
