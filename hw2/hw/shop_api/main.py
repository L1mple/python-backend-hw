from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .api.cart import router as cart_router
from .api.item import router as item_router

app = FastAPI(title="Shop API")
app.include_router(cart_router)
app.include_router(item_router)

Instrumentator().instrument(app).expose(app)
