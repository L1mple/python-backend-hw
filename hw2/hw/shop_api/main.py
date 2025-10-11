from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .routers import items, carts
from .factory import ItemCreate
from .database import db


app = FastAPI(title="Shop API")

Instrumentator().instrument(app).expose(app)

app.include_router(items.router)
app.include_router(carts.router)
