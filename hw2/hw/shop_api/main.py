from __future__ import annotations
from fastapi import FastAPI
from shop_api.api.items import router as items_router
from shop_api.api.carts import router as carts_router

from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

app.include_router(items_router)
app.include_router(carts_router)