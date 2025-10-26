from fastapi import FastAPI

from shop_api.api.cart_routes import router as cart_router
from shop_api.api.chat_routes import router as chat_router
from shop_api.api.item_routes import router as item_router

app = FastAPI(title="Shop API")

app.include_router(item_router)
app.include_router(cart_router)
app.include_router(chat_router)
