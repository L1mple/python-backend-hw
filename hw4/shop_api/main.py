from fastapi import FastAPI

from shop_api.routers.cart import router as cart
from shop_api.routers.item import router as item

from prometheus_fastapi_instrumentator import Instrumentator

from .db import Base, engine

app = FastAPI(title="Shop API")

app.include_router(cart)
app.include_router(item)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
Base.metadata.create_all(bind=engine)
