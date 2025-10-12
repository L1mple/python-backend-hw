from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from shop_api.routers import cart_router, item_router, chat_router

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)
app.include_router(cart_router)
app.include_router(item_router)
app.include_router(chat_router)