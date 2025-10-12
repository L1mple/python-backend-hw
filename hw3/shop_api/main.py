from fastapi import FastAPI
from shop_api.routers import items, carts, chat
from prometheus_fastapi_instrumentator import Instrumentator


app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

app.include_router(items.router)
app.include_router(carts.router)
app.include_router(chat.router)