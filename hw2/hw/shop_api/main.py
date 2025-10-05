from fastapi import FastAPI
from .routers import items
from .routers import carts
app = FastAPI(title="Shop API")
app.include_router(items.router)
app.include_router(carts.router)