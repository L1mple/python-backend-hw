from fastapi import FastAPI
from shop_api.routers import cart_router, item_router, chat_router


app = FastAPI(title="Shop API")
app.include_router(cart_router)
app.include_router(item_router)
app.include_router(chat_router)