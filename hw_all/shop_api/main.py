from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from . import cart_routes, chat_routes, item_routes
from .database import init_db


init_db()

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

app.include_router(item_routes.router)
app.include_router(cart_routes.router)
app.include_router(chat_routes.router)
