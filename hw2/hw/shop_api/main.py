from fastapi import FastAPI

from prometheus_fastapi_instrumentator import Instrumentator

from .shop.routes.item import router as items_router
from .shop.routes.cart import router as cart_router

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

app.include_router(items_router)
app.include_router(cart_router)
