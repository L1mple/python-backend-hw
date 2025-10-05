from __future__ import annotations
from fastapi import FastAPI
from shop_api.api.items import router as items_router
from shop_api.api.carts import router as carts_router

app = FastAPI(title="Shop API")
app.include_router(items_router)
app.include_router(carts_router)
